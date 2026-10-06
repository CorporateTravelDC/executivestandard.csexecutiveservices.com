#!/usr/bin/env python3
"""template-rss-location.py -- write the nginx include that serves the private
Substack-importer feed UNGATED at its secret path on the members vhost.

The members vhost (nginx/members.executivestandard.csexecutiveservices.com.*)
gates everything behind auth_request and pulls in
    /etc/nginx/executivestandard-rss-location*.conf
as a glob (non-fatal if absent). This script is what finally templates that
file: the secret feed path IS the credential, so the file is root:root 0600
and the token is read from config.json (gitignored, build-time) and written
straight to the include -- never printed, never passed on argv.

2026-10-03: needed because executivestandard.csexecutiveservices.com is being
handed to Substack as its custom domain; the feed Substack polls must be
served from the members host, which otherwise answers the path with the
branded invite page (HTTP 200, text/html -- not XML).

Run as root:  sudo python3 scripts/template-rss-location.py && sudo nginx -t && sudo systemctl reload nginx
Re-run after any SECRET_RSS_TOKEN rotation (then regenerate the feed).
"""
import json
import os
import re
import sys

CONFIG = "/opt/corporatetraveldc/private/executivestandard-website/config.json"
OUT = "/etc/nginx/executivestandard-rss-location.conf"

def main() -> int:
    if os.geteuid() != 0:
        print("template-rss-location: run as root (writes a root-only file under /etc/nginx)", file=sys.stderr)
        return 1
    with open(CONFIG, encoding="utf-8") as f:
        tok = (json.load(f).get("SECRET_RSS_TOKEN") or "").strip()
    if not tok or tok.startswith("REPLACE_") or not re.fullmatch(r"[A-Za-z0-9]{16,64}", tok):
        print("template-rss-location: SECRET_RSS_TOKEN missing/placeholder/unsafe in config.json", file=sys.stderr)
        return 2
    body = (
        "# Private Substack-importer feed. The secret path IS the credential; the file\n"
        "# itself is root:root 0600 and templated by scripts/template-rss-location.py.\n"
        f"location = /feed{tok}.xml {{\n"
        "    auth_request off;\n"
        "    try_files $uri =404;\n"
        "    add_header Cache-Control \"no-store\" always;\n"
        "    add_header X-Robots-Tag \"noindex,nofollow\" always;\n"
        "}\n"
    )
    fd = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(OUT, 0o600)
    print(f"template-rss-location: wrote {OUT} (0600). Now: nginx -t && systemctl reload nginx")
    return 0

if __name__ == "__main__":
    sys.exit(main())
