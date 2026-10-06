#!/usr/bin/env python3
"""es-access — Executive Standard entitlements control plane.

Self-owned readership management: issue/see/modify/cap/revoke access grants
across any source (Substack, Patreon, LinkedIn, collaborator comps) without
running any of it inside Substack. Backs exec_standard_tokens /
exec_standard_sources in the corporatetraveldc Postgres. Talks to the DB via
`podman exec ... psql` (same path the platform already uses; no extra deps).

  es-access issue <email> --source substack-seed [--campaign c] [--days N] [--notes ...]
  es-access list [--source s] [--campaign c] [--status active|revoked|all]
  es-access stats [--source s] [--campaign c]     # how many run, when, remaining under cap
  es-access extend <token> <+Nd>                  # push expiry out
  es-access promo  <token> "<note>" [--days N]    # annotate (+ optional extend)
  es-access revoke <token>
  es-access source list
  es-access source enable|disable <source>
  es-access source cap <source> <N|none>
"""
import argparse, subprocess, secrets, sys, re, os

BASE_URL = "https://members.executivestandard.csexecutiveservices.com"

def _pw():
    try:
        for line in open("/etc/corporatetraveldc/dispatch-secrets.env"):
            if line.startswith("DISPATCH_PG_PASSWORD="):
                return line.split("=",1)[1].strip().strip('"')
    except OSError: pass
    sys.exit("XX cannot read DISPATCH_PG_PASSWORD")

def q(sql, *params):
    """Parameterized query via psql -v (psql :'pN' quoting is injection-safe).
    PGPASSWORD is passed by NAME (-e PGPASSWORD) with the value only in the
    child process env, so it never appears in the podman argv / ps output."""
    full = ["podman","exec","-i","-e","PGPASSWORD","corporatetraveldc-pgsql",
            "psql","-U","dispatch","-d","corporatetraveldc","-At","-F","|"]
    for i,p in enumerate(params,1):
        full += ["-v", f"p{i}={p}"]
    child_env = dict(os.environ, PGPASSWORD=_pw())
    r = subprocess.run(full, input=sql, capture_output=True, text=True, env=child_env)
    if r.returncode != 0:
        sys.exit(f"XX psql: {r.stderr.strip()}")
    return [ln for ln in r.stdout.splitlines() if ln]

def _match_one(prefix):
    """Resolve a token prefix to EXACTLY one token, or refuse. Guards against
    a short/empty prefix mass-matching (revoke '' -> LIKE '%' -> all)."""
    if not prefix or len(prefix) < 12:
        sys.exit("XX token prefix must be at least 12 characters")
    rows = q("SELECT token FROM exec_standard_tokens WHERE token LIKE :'p1' || '%';", prefix)
    if not rows: sys.exit("XX no token matches that prefix")
    if len(rows) > 1: sys.exit(f"XX {len(rows)} tokens match '{prefix[:16]}…' — be more specific")
    return rows[0]


def issue(a):
    rows = q("SELECT enabled, cap, (SELECT count(*) FROM exec_standard_tokens t "
             "WHERE t.source=s.source AND t.status='active') FROM exec_standard_sources s "
             "WHERE source=:'p1';", a.source)
    if not rows: sys.exit(f"XX unknown source '{a.source}' (see: es-access source list)")
    enabled, cap, active = rows[0].split("|")
    if enabled != "t": sys.exit(f"XX source '{a.source}' is DISABLED — enable it first")
    if cap and cap != "" and int(active) >= int(cap):
        sys.exit(f"XX source '{a.source}' cap reached ({active}/{cap}) — raise cap or pick another source")
    token = secrets.token_urlsafe(32)
    exp = "NULL" if not a.days else f"now() + interval '{int(a.days)} days'"
    # insert only while source enabled AND under cap. Closes the common race; under
    # heavy concurrency READ COMMITTED can still let two inserts pass (single-admin CLI, moot).
    out = q(f"INSERT INTO exec_standard_tokens (token,email,source,campaign,expires_at,notes) "
      f"SELECT :'p1',:'p2',:'p3',:'p4',{exp},:'p5' "
      f"WHERE (SELECT enabled FROM exec_standard_sources WHERE source=:'p3') = true "
      f"AND ((SELECT cap FROM exec_standard_sources WHERE source=:'p3') IS NULL "
      f"OR (SELECT count(*) FROM exec_standard_tokens WHERE source=:'p3' AND status='active') "
      f"< (SELECT cap FROM exec_standard_sources WHERE source=:'p3')) RETURNING token;",
      token, a.email or "", a.source, a.campaign or "", a.notes or "")
    if not out:
        sys.exit(f"XX not issued — source '{a.source}' is disabled or at cap (raced)")
    print(f"OK  issued  source={a.source}  email={a.email or '-'}  campaign={a.campaign or '-'}"
          + (f"  expires=+{a.days}d" if a.days else "  expires=never"))
    print(f"    invite link:  {BASE_URL}/?token={token}")

def _list(a):
    where = ["1=1"]
    if a.source: where.append("source=:'p1'")
    st = getattr(a,'status','active')
    if st and st != "all": where.append(f"status='{st}'" if st in ('active','revoked') else "1=1")
    sql = ("SELECT left(token,10)||'…', coalesce(email,'-'), source, coalesce(campaign,'-'), "
           "status, coalesce(to_char(expires_at,'YYYY-MM-DD'),'never'), "
           "coalesce(to_char(redeemed_at,'YYYY-MM-DD HH24:MI'),'-') "
           f"FROM exec_standard_tokens WHERE {' AND '.join(where)} ORDER BY issued_at DESC LIMIT 200;")
    rows = q(sql, *( [a.source] if a.source else [] ))
    print(f"  {'TOKEN':12} {'EMAIL':28} {'SOURCE':18} {'CAMPAIGN':16} {'ST':7} {'EXPIRES':11} RUN")
    for r in rows:
        c = r.split("|")
        print(f"  {c[0]:12} {c[1][:28]:28} {c[2]:18} {c[3]:16} {c[4]:7} {c[5]:11} {c[6]}")
    print(f"  ({len(rows)} row(s))")

def stats(a):
    # fixed param slots: p1=source filter, p2=campaign filter ('' = no filter)
    sql=("SELECT source, coalesce(campaign,'-'), count(*) issued, "
         "count(*) FILTER (WHERE redeemed_at IS NOT NULL) run, "
         "count(*) FILTER (WHERE status='active') active, "
         "count(*) FILTER (WHERE status='revoked') revoked "
         "FROM exec_standard_tokens "
         "WHERE (:'p1'='' OR source=:'p1') AND (:'p2'='' OR campaign=:'p2') "
         "GROUP BY source, campaign ORDER BY source, campaign;")
    rows=q(sql, a.source or "", a.campaign or "")
    print(f"  {'SOURCE':18} {'CAMPAIGN':18} {'ISSUED':7} {'RUN':5} {'ACTIVE':7} REVOKED   (cap)")
    caps={r.split('|')[0]: r.split('|')[1] for r in q("SELECT source, coalesce(cap::text,'∞') FROM exec_standard_sources;")}
    for r in rows:
        c=r.split("|")
        cap=caps.get(c[0],'∞'); rem = "∞" if cap=='∞' else str(max(0,int(cap)-int(c[4])))
        print(f"  {c[0]:18} {c[1]:18} {c[2]:7} {c[3]:5} {c[4]:7} {c[5]:9} {cap} (rem {rem})")
    # redemption timeline for a campaign
    if a.campaign:
        print(f"\n  redemptions for campaign '{a.campaign}' (how many run, when):")
        for r in q("SELECT to_char(redeemed_at,'YYYY-MM-DD HH24:MI'), coalesce(email,'-'), source "
                   "FROM exec_standard_tokens WHERE campaign=:'p1' AND redeemed_at IS NOT NULL "
                   "ORDER BY redeemed_at;", a.campaign):
            c=r.split("|"); print(f"    {c[0]}  {c[1]}  ({c[2]})")

def extend(a):
    m=re.match(r"\+?(\d+)d?$", a.delta)
    if not m: sys.exit("XX delta must look like +30d")
    tok=_match_one(a.token)
    q(f"UPDATE exec_standard_tokens SET expires_at = coalesce(expires_at,now()) + interval '{int(m.group(1))} days' "
        "WHERE token = :'p1';", tok)
    print(f"OK  extended token {tok[:12]}… by {m.group(1)}d")

def promo(a):
    exp = f", expires_at = coalesce(expires_at,now()) + interval '{int(a.days)} days'" if a.days else ""
    tok=_match_one(a.token)
    q(f"UPDATE exec_standard_tokens SET notes = coalesce(notes||' | ','') || :'p2'{exp} "
        "WHERE token = :'p1';", tok, a.note)
    print(f"OK  promo note applied to {tok[:12]}…" + (f" (+{a.days}d)" if a.days else ""))

def revoke(a):
    tok=_match_one(a.token)
    q("UPDATE exec_standard_tokens SET status='revoked' WHERE token = :'p1';", tok)
    print(f"OK  revoked token {tok[:12]}… — effective on next request")

def source_cmd(a):
    if a.action=="list":
        print(f"  {'SOURCE':26} {'ENABLED':8} {'CAP':6} LABEL")
        for r in q("SELECT source, enabled, coalesce(cap::text,'∞'), coalesce(label,'') FROM exec_standard_sources ORDER BY enabled DESC, source;"):
            c=r.split("|"); print(f"  {c[0]:26} {('yes' if c[1]=='t' else 'no'):8} {c[2]:6} {c[3]}")
    elif a.action in ("enable","disable"):
        q(f"UPDATE exec_standard_sources SET enabled={'true' if a.action=='enable' else 'false'} WHERE source=:'p1';", a.name)
        print(f"OK  source '{a.name}' {a.action}d")
    elif a.action=="cap":
        cap = "NULL" if a.value.lower() in ("none","null","∞","") else str(int(a.value))
        q(f"UPDATE exec_standard_sources SET cap={cap} WHERE source=:'p1';", a.name)
        print(f"OK  source '{a.name}' cap = {a.value}")

def main():
    p=argparse.ArgumentParser(prog="es-access"); sub=p.add_subparsers(dest="cmd", required=True)
    i=sub.add_parser("issue"); i.add_argument("email"); i.add_argument("--source",required=True); i.add_argument("--campaign"); i.add_argument("--days",type=int); i.add_argument("--notes"); i.set_defaults(fn=issue)
    l=sub.add_parser("list"); l.add_argument("--source"); l.add_argument("--campaign"); l.add_argument("--status",default="active"); l.set_defaults(fn=_list)
    s=sub.add_parser("stats"); s.add_argument("--source"); s.add_argument("--campaign"); s.set_defaults(fn=stats)
    e=sub.add_parser("extend"); e.add_argument("token"); e.add_argument("delta"); e.set_defaults(fn=extend)
    pr=sub.add_parser("promo"); pr.add_argument("token"); pr.add_argument("note"); pr.add_argument("--days",type=int); pr.set_defaults(fn=promo)
    rv=sub.add_parser("revoke"); rv.add_argument("token"); rv.set_defaults(fn=revoke)
    sc=sub.add_parser("source"); sc.add_argument("action",choices=["list","enable","disable","cap"]); sc.add_argument("name",nargs="?"); sc.add_argument("value",nargs="?"); sc.set_defaults(fn=source_cmd)
    a=p.parse_args(); a.fn(a)

if __name__=="__main__": main()
