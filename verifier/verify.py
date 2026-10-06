#!/usr/bin/env python3
"""Executive Standard gate verifier -- members auth_request brain + the public
invite host (2026-10-05 rewrite).

Runs in the poller image (PYTHONPATH=/app/src, Postgres socket) so it shares
ONE implementation with the dispatch console and CLI:
ctdi-dispatch-internal/src/common/es_invites.py (schema pg_schema/0072).

Routing is by the PATH nginx proxies to, never by a request header (a client
can send any header; on an auth_request subrequest a header-selected 200 would
open the gate):
  /auth            members auth_request: session cookie __Host-es_s live? 200 / 401.
                   The pre-invite cookie es_auth is still honoured against
                   exec_standard_tokens until `es-invite.sh retire-legacy`.
  /redeem          members ?x=<hand-off> -> 302 / + Set-Cookie (single use).
  /_invite/...     the invite host (invite.executivestandard.csexecutiveservices.com
                   proxies http://127.0.0.1:8787/_invite$uri; the members vhost
                   only ever proxies the two fixed URLs above):
      GET  /             landing: type a promo code, or open your invite link
      GET  /i/<code>     "Open The Executive Standard" button -- a GET spends
                         nothing, so link previews (iMessage, Slack, mail
                         scanners) cannot burn an invite
      POST /i/<code>     -> 303 to the members hand-off
      GET  /p[?code=]    promo form (prefilled from a QR / link)
      POST /p            -> 303 to the members hand-off
  anything else    401.
DB is the authority: revoke / expiry / freeze / source-disable take effect on
the next request. Fails closed on any DB error.
"""
import html
import http.server
import os
import urllib.parse

from common import db
from common import es_invites as es

PORT = int(os.environ.get("VERIFY_PORT", "8787"))
COOKIE = "__Host-es_s"
LEGACY_COOKIE = "es_auth"
COOKIE_MAX_AGE = 400 * 86400          # browser ceiling; the server-side idle limit is es.SESSION_IDLE_S
SUBSTACK = "https://executivestandard.substack.com/subscribe"
MAX_BODY = 2048
INVITE_PREFIX = "/_invite"


def cookie_of(header, name):
    for part in (header or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip() == name:
                return v.strip()
    return ""


def _legacy_valid(tok):
    if not tok or len(tok) > 128:
        return False
    try:
        with db.conn() as c:
            return c.execute(
                "SELECT 1 FROM exec_standard_tokens t JOIN exec_standard_sources s ON t.source = s.source "
                "WHERE t.token = ? AND t.status = 'active' AND (t.expires_at IS NULL OR t.expires_at > now()) "
                "AND s.enabled = true", (tok,)).fetchone() is not None
    except Exception:
        return False


_CSS = ("<style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;"
        "place-items:center;font-family:Georgia,'Times New Roman',serif;background:#0a1628;color:#e9e6e0;"
        "padding:24px;line-height:1.6}.card{width:100%;max-width:30rem;text-align:center}"
        ".mark{font-family:ui-monospace,monospace;font-size:.72rem;letter-spacing:.28em;text-transform:uppercase;"
        "color:#9c8f78;margin-bottom:1.6rem}h1{font-size:clamp(1.6rem,6vw,2.3rem);margin:0 0 1rem;font-weight:600;"
        "text-wrap:balance}p{color:#b9b3a8;font-size:1.05rem;margin:0 0 1.2rem}.err{color:#e7a17a;font-style:italic}"
        "input{width:100%;font:1.15rem ui-monospace,monospace;letter-spacing:.12em;text-align:center;"
        "text-transform:uppercase;padding:.8rem;background:#161b21;color:#e9e6e0;border:1px solid #3a424c;"
        "border-radius:2px;margin-bottom:.9rem}input:focus,button:focus,a:focus{outline:2px solid #d8b673;"
        "outline-offset:2px}button{display:inline-block;width:100%;padding:.9rem 1.4rem;border:1px solid #6d7d6f;"
        "border-radius:2px;background:#16241c;color:#cfe0d1;font:.85rem ui-monospace,monospace;letter-spacing:.08em;"
        "text-transform:uppercase;cursor:pointer}a.quiet{color:#9c8f78;font-size:.9rem}"
        "hr{border:0;border-top:1px solid #2a2f36;margin:1.8rem 0}.logo{display:block;margin:0 auto 1rem;"
        "border-radius:16px}</style>")


# Brand: the blog's own icon set, served ungated by the members host (/icons/).
_BRAND = "https://members.executivestandard.csexecutiveservices.com"
_ICONS = (f"<link rel='icon' type='image/png' sizes='32x32' href='{_BRAND}/icons/favicon-32.png'>"
          f"<link rel='apple-touch-icon' sizes='180x180' href='{_BRAND}/icons/apple-touch-icon.png'>")


def _page(title, body, status=200):
    doc = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           "<meta name='robots' content='noindex,nofollow'><meta name='referrer' content='no-referrer'>"
           f"<meta name='theme-color' content='#0a1628'>{_ICONS}"
           f"<title>{html.escape(title)} -- The Executive Standard</title>{_CSS}</head><body><main class='card'>"
           f"<img class='logo' src='{_BRAND}/icons/icon-192.png' alt='' width='72' height='72'>"
           f"<div class='mark'>The Executive Standard</div>{body}</main></body></html>")
    return status, doc


def _promo_form(prefill="", error=""):
    err = f"<p class='err' role='alert'>{html.escape(error)}</p>" if error else ""
    return ("<h1>Have a code?</h1><p>Enter the code you were given to read the full edition.</p>" + err +
            "<form method='post' action='/p'><label for='code' class='mark' style='display:block;margin:0 0 .4rem'>"
            "Promo code</label><input id='code' name='code' autocomplete='off' autocapitalize='characters' "
            f"spellcheck='false' placeholder='ES-XXXX-XXXX-XX' value='{html.escape(prefill, quote=True)}' required>"
            "<button type='submit'>Read the full edition</button></form>")


def _landing():
    return _page("Invitation", _promo_form() +
                 "<hr><p>Have a personal invitation? Open the link from your invitation on this device.</p>"
                 f"<a class='quiet' href='{SUBSTACK}'>Not invited yet? Subscribe on Substack</a>")


def _invite_button(code):
    return _page("Your invitation",
                 "<h1>You're invited</h1><p>This opens the full, unabridged edition on this device.</p>"
                 f"<form method='post' action='/i/{urllib.parse.quote(code, safe='')}'>"
                 "<button type='submit'>Open The Executive Standard</button></form>")


class H(http.server.BaseHTTPRequestHandler):
    server_version = "es-gate"
    sys_version = ""

    def _send(self, status, body="", headers=()):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in headers:
            self.send_header(k, v)
        if data:
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD" and data:
            self.wfile.write(data)

    # -- members host ---------------------------------------------------------------
    def _auth(self):
        cookies = self.headers.get("Cookie")
        try:
            ok = es.session_check(cookie_of(cookies, COOKIE)) is not None
        except Exception:
            ok = False                                     # fail closed
        if not ok:
            ok = _legacy_valid(cookie_of(cookies, LEGACY_COOKIE))
        self._send(200 if ok else 401)

    def _redeem(self):
        uri = self.headers.get("X-Original-URI", "")
        qs = urllib.parse.parse_qs(uri.split("?", 1)[1]) if "?" in uri else {}
        try:
            secret, _ = es.exchange((qs.get("x") or [""])[0])
        except Exception:
            return self._send(302, headers=[("Location", "/")])   # bare path -> 401 -> branded invite page
        self._send(302, headers=[("Location", "/"),
                                 ("Set-Cookie", f"{COOKIE}={secret}; Max-Age={COOKIE_MAX_AGE}; Path=/; Secure; "
                                                "HttpOnly; SameSite=Lax")])

    # -- invite host ----------------------------------------------------------------
    def _form(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return {}
        return urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "replace"))

    def _invite(self, path, query):
        if self.command in ("GET", "HEAD"):
            if path == "/":
                return self._send(*_landing())
            if path == "/p":
                prefill = (urllib.parse.parse_qs(query).get("code") or [""])[0][:20]
                return self._send(*_page("Promo code", _promo_form(prefill=prefill)))
            if path.startswith("/i/"):
                return self._send(*_invite_button(path[3:]))
            return self._send(404)
        if self.command != "POST":
            return self._send(405)
        try:
            if path.startswith("/i/"):
                return self._send(303, headers=[("Location", es.claim_invite(urllib.parse.unquote(path[3:])))])
            if path == "/p":
                return self._send(303, headers=[("Location", es.redeem_promo((self._form().get("code") or [""])[0]))])
        except es.InviteError as e:
            if path.startswith("/i/"):
                return self._send(*_page("Invitation", "<h1>Invitation</h1>"
                                         f"<p class='err' role='alert'>{html.escape(e.detail)}</p>"
                                         "<a class='quiet' href='/'>Have a promo code instead?</a>", e.status))
            return self._send(*_page("Promo code", _promo_form(error=e.detail), e.status))
        except Exception:
            return self._send(*_page("Unavailable", "<h1>Something went wrong</h1><p>Please try again in a minute.</p>",
                                     503))
        self._send(404)

    def _route(self):
        parts = urllib.parse.urlsplit(self.path)
        if parts.path == INVITE_PREFIX or parts.path.startswith(INVITE_PREFIX + "/"):
            return self._invite(parts.path[len(INVITE_PREFIX):] or "/", parts.query)
        if self.command not in ("GET", "HEAD"):
            return self._send(405)
        if parts.path == "/redeem":
            return self._redeem()
        if parts.path == "/auth":
            return self._auth()
        self._send(401)

    do_GET = do_HEAD = do_POST = _route

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
