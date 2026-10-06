/**
 * functions/_middleware.js — Executive Standard access gate (Cloudflare Pages).
 *
 * FAILS CLOSED. Every host that reaches this Function is gated — the custom
 * domain, executivestandard.pages.dev, and per-deploy preview URLs all get the
 * invite gate. The apex csexecutiveservices.com is a different origin and never
 * routes here, so there is nothing to "pass through": passing anything through
 * is how the old version leaked pages.dev.
 *
 * ADMISSION is a SIGNED, EXPIRING cookie — never a static word. The cookie is
 *     es_auth = <expiry>.<hex(HMAC_SHA256(SIGNING_SECRET, <expiry>))>
 * verified constant-time on every request. A valid ?token=<INVITE_TOKEN> mints
 * that cookie and 302-redirects to a clean URL so the token never persists in
 * history, logs, or Referer. The nginx mirror runs the byte-identical
 * construction via its verifier container, so the two gates cannot diverge.
 *
 * Secrets come from Pages env bindings (SIGNING_SECRET, INVITE_TOKEN,
 * SECRET_RSS_TOKEN) — never a deployed file.
 */

const GATED_HOSTS = new Set([
  "executivestandard.csexecutiveservices.com",
]);
const ALLOW_PAGES_DEV = true; // pages.dev/preview reach this Function; gate them, don't pass them.

const COOKIE = "es_auth";
const MAX_AGE = 60 * 60 * 24 * 30; // 30 days
const INVITE_EMAIL = "executivestandard@csexecutiveservices.com";
const SUBSTACK_MIRROR = "https://executivestandard.substack.com";
const PROBE_PATHS = new Set(["/feed", "/feed.xml", "/index.xml", "/rss", "/rss.xml"]);
const FORBIDDEN_EXACT = new Set(["/config.json", "/manifest.sha256", "/manifest.sha256.asc"]);
const FORBIDDEN_PREFIX = ["/security/", "/functions/", "/verifier/"];

export async function onRequest(context) {
  const { request, next, env } = context;
  const url = new URL(request.url);

  // --- HOST NORMALISE + FAIL-CLOSED FIREWALL ---
  const host = url.hostname.replace(/\.$/, "").toLowerCase(); // strip trailing dot
  const hostOk = GATED_HOSTS.has(host) || (ALLOW_PAGES_DEV && host.endsWith(".pages.dev"));
  if (!hostOk) {
    // Unknown host reaching this Function is unexpected — deny, don't serve.
    return new Response("Not found", { status: 404, headers: { "cache-control": "no-store" } });
  }

  const SIGNING_SECRET = (env && env.SIGNING_SECRET) || "";
  const INVITE_TOKEN = (env && env.INVITE_TOKEN) || "";
  const SECRET_RSS_TOKEN = (env && env.SECRET_RSS_TOKEN) || "";
  if (!SIGNING_SECRET) return gate(500, false); // misconfig fails closed

  // --- PATH NORMALISE (decode once, lower-case, reject residual traversal) ---
  let path;
  try { path = decodeURIComponent(url.pathname); } catch { return gate(400, false); }
  if (path.includes("%2e") || path.includes("%2f") || path.includes("..") || path.includes("//")) {
    return gate(400, false);
  }
  const lpath = path.toLowerCase();

  // --- FORBIDDEN (case-insensitive, both exact and prefix incl. bare form) ---
  if (FORBIDDEN_EXACT.has(lpath) ||
      FORBIDDEN_PREFIX.some((p) => lpath === p.slice(0, -1) || lpath.startsWith(p))) {
    return gate(403, false);
  }

  // --- PATH RULE 1: private RSS token path (constant-time) ---
  if (SECRET_RSS_TOKEN && safeEqual(lpath, `/feed${SECRET_RSS_TOKEN}.xml`.toLowerCase())) {
    return noStore(await next());
  }

  // --- PATH RULE 2: branded probe suppression ---
  if (PROBE_PATHS.has(lpath)) return gate(200, true);

  // --- PATH RULE 3a: valid signed cookie → admit ---
  const cookies = parseCookies(request.headers.get("Cookie") || "");
  if (await verifyCookie(cookies[COOKIE], SIGNING_SECRET)) {
    return noStore(await next());
  }

  // --- PATH RULE 3b: valid invite token → mint cookie, 302 to clean URL ---
  const queryToken = url.searchParams.get("token") || "";
  if (INVITE_TOKEN && safeEqual(queryToken, INVITE_TOKEN)) {
    const value = await mintCookie(SIGNING_SECRET);
    const clean = new URL(url); clean.searchParams.delete("token");
    return new Response(null, {
      status: 302,
      headers: {
        "location": clean.pathname + (clean.search || "") ,
        "set-cookie": `${COOKIE}=${value}; Max-Age=${MAX_AGE}; Path=/; Secure; HttpOnly; SameSite=Lax`,
        "cache-control": "no-store",
        "referrer-policy": "no-referrer",
      },
    });
  }

  // --- No credential → branded Invitation Required ---
  return gate(401, PROBE_PATHS.has(lpath));
}

// ---- sealed-cookie crypto: AES-256-GCM (opaque, authenticated) ----------------
// The cookie is base64url(iv[12] || ciphertext || gcmTag[16]) with the expiry
// ENCRYPTED inside. Opaque structure, tamper-proof via the GCM tag. The nginx
// verifier container (verifier/verify.js) runs the byte-identical construction
// with the same SIGNING_SECRET, so both gates accept/reject the same cookies.
// Key = SHA-256(SIGNING_SECRET) -> 256-bit AES key (deterministic, shared).
const b64u = {
  enc: (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,""),
  dec: (str) => { const b = atob(str.replace(/-/g,"+").replace(/_/g,"/")); const u=new Uint8Array(b.length); for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i); return u; },
};
async function aesKey(secret) {
  const raw = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(secret));
  return crypto.subtle.importKey("raw", raw, { name: "AES-GCM" }, false, ["encrypt","decrypt"]);
}
async function mintCookie(secret) {
  const expiry = String(Math.floor(Date.now()/1000) + MAX_AGE);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await aesKey(secret);
  const ct = new Uint8Array(await crypto.subtle.encrypt(
    { name:"AES-GCM", iv }, key, new TextEncoder().encode(expiry)));
  const out = new Uint8Array(iv.length + ct.length);
  out.set(iv, 0); out.set(ct, iv.length);
  return b64u.enc(out);
}
async function verifyCookie(value, secret) {
  if (!value) return false;
  try {
    const blob = b64u.dec(value);
    if (blob.length < 12 + 16 + 1) return false;
    const iv = blob.slice(0,12), ct = blob.slice(12);
    const key = await aesKey(secret);
    const pt = new TextDecoder().decode(await crypto.subtle.decrypt(
      { name:"AES-GCM", iv }, key, ct)); // throws on bad tag = forgery/tamper
    if (!/^\d+$/.test(pt)) return false;
    return Number(pt) >= Math.floor(Date.now()/1000); // not expired
  } catch { return false; }
}

function noStore(resp) {
  const out = new Response(resp.body, resp);
  out.headers.set("Cache-Control", "private, no-store");
  out.headers.set("Vary", "Cookie");
  out.headers.set("Referrer-Policy", "no-referrer");
  return out;
}
function parseCookies(header) {
  const out = {};
  for (const part of header.split(";")) {
    const i = part.indexOf("=");
    if (i > -1) out[part.slice(0, i).trim()] = part.slice(i + 1).trim();
  }
  return out;
}
function safeEqual(a, b) {
  const enc = new TextEncoder(); const ba = enc.encode(a), bb = enc.encode(b);
  let diff = ba.length ^ bb.length; const n = Math.max(ba.length, bb.length);
  for (let i = 0; i < n; i++) diff |= (ba[i] || 0) ^ (bb[i] || 0);
  return diff === 0;
}
function gate(status, probe) {
  const notice = probe
    ? `<p class="notice">You are attempting to reach a private subscription, please reach out to the publication staff for a proper access token.</p>` : "";
  const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Executive Standard — Invitation Required</title><style>:root{color-scheme:light dark}body{margin:0;min-height:100vh;display:grid;place-items:center;font-family:Georgia,serif;background:#0f1216;color:#e9e6e0;padding:24px;line-height:1.6}.card{max-width:34rem;text-align:center}.mark{font-family:ui-monospace,monospace;font-size:.72rem;letter-spacing:.28em;text-transform:uppercase;color:#9c8f78;margin-bottom:1.6rem}h1{font-size:clamp(1.7rem,5vw,2.5rem);margin:0 0 1rem;font-weight:600}p{color:#b9b3a8;margin:0 0 1.2rem}.notice{color:#d8b673;font-style:italic;border-top:1px solid #2a2f36;border-bottom:1px solid #2a2f36;padding:1rem 0;margin:1.6rem 0}a.cta{display:inline-block;margin-top:.6rem;padding:.75rem 1.6rem;border:1px solid #6d7d6f;color:#cfe0d1;text-decoration:none;font-family:ui-monospace,monospace;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase}</style><div class="card"><div class="mark">The Executive Standard</div><h1>Invitation Required</h1><p>The Executive Standard is a private publication. Access is by invitation.</p>${notice}<p>Have an invitation link? Open it and you will be admitted automatically. Otherwise, request one below.</p><a class="cta" href="mailto:${INVITE_EMAIL}?subject=Executive%20Standard%20invitation%20request">Request an invitation</a><p style="margin-top:1.4rem;font-size:.85rem"><a style="color:#7d8794" href="${SUBSTACK_MIRROR}">Or read the mirror on Substack &rarr;</a></p></div>`;
  return new Response(html, { status, headers: {
    "content-type": "text/html; charset=utf-8", "cache-control": "no-store",
    "x-robots-tag": "noindex, nofollow", "referrer-policy": "no-referrer" } });
}
