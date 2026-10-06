#!/usr/bin/env python3
"""generate-private-feed.py — build the tokenised private RSS feed.

This is the point of the Executive Standard lockdown: a secret feed at
    /feed<SECRET_RSS_TOKEN>.xml
that ONLY Substack's Private-Mode RSS importer (holding the token path) can
pull, so posts land as Substack drafts. The middleware / nginx gate serve this
exact path and suppress every ordinary /feed probe.

Body fidelity: each item's <content:encoded> is the <article>…</article> block
lifted verbatim from the already-built HTML in --html, so the feed body is
identical to the published page and the site's custom Markdown converter is
never duplicated (and cannot drift). A post whose HTML isn't built yet degrades
to title + description + link rather than being dropped silently — it prints a
warning so you know to build it.

Token source: config.json (build-time, gitignored, never deployed). Never pass
the token on argv — it would land in the process list.
"""
import argparse, json, os, re, sys
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape

def load_token(cfg_path):
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    tok = (cfg.get("SECRET_RSS_TOKEN") or "").strip()
    if not tok or tok.startswith("REPLACE_"):
        sys.exit("XX SECRET_RSS_TOKEN missing/placeholder in config.json")
    return tok

def parse_frontmatter(raw):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            # render_markdown() YAML-quotes any title/description containing
            # ':' etc. This parser is not a YAML parser, so strip one layer of
            # matching quotes (and \" escapes) or they leak into <title> as
            # literal &quot;...&quot; -- which is exactly what the feed showed
            # for six articles until 2026-10-03.
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1].replace('\\"', '"')
            fm[k.strip()] = v
    return fm

def article_html(html_dir, slug):
    p = os.path.join(html_dir, slug + ".html")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        s = f.read()
    m = re.search(r"<article\b[^>]*>(.*?)</article>", s, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None

def rfc822(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt), dt
    except Exception:
        now = datetime.now(timezone.utc)
        return format_datetime(now), now

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--md", default="_md")
    ap.add_argument("--html", default="/var/www/executivestandard.csexecutiveservices.com")
    ap.add_argument("--out", default="/var/www/executivestandard.csexecutiveservices.com")
    ap.add_argument("--base", default="https://executivestandard.csexecutiveservices.com")
    ap.add_argument("--title", default="The Executive Standard")
    ap.add_argument("--desc", default="Private subscriber feed — The Executive Standard.")
    a = ap.parse_args()

    token = load_token(a.config)
    items, warnings = [], []
    for fn in sorted(os.listdir(a.md)):
        if not fn.endswith(".md"): continue
        if fn == "index.md" or fn.startswith("teaser-"): continue
        slug = fn[:-3]
        with open(os.path.join(a.md, fn), encoding="utf-8") as f:
            fm = parse_frontmatter(f.read())
        title = fm.get("title")
        date = fm.get("date")
        if not (title and date):
            warnings.append(f"skip {fn}: missing title/date"); continue
        status = (fm.get("status") or "").lower()
        draft = (fm.get("draft") or "").lower()
        if draft in ("true","yes","1") or status in ("draft","unpublished","private"):
            warnings.append(f"skip {fn}: marked draft/unpublished"); continue
        if not status and draft == "":
            warnings.append(f"{fn}: no status:/draft: flag -- INCLUDED; add 'status: published' to be explicit")
        link = fm.get("source") or f"{a.base}/{slug}.html"
        desc = fm.get("description", "")
        pubdate, dt = rfc822(date)
        body = article_html(a.html, slug)
        if body is None:
            warnings.append(f"{fn}: no built HTML at {slug}.html — degraded to summary")
        items.append((dt, title, link, desc, pubdate, body))

    items.sort(key=lambda x: x[0], reverse=True)
    now822 = format_datetime(datetime.now(timezone.utc))

    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
             'xmlns:atom="http://www.w3.org/2005/Atom">', '<channel>',
             f'<title>{escape(a.title)}</title>',
             f'<link>{escape(a.base)}/</link>',
             f'<description>{escape(a.desc)}</description>',
             '<language>en-us</language>',
             f'<lastBuildDate>{now822}</lastBuildDate>',
             f'<atom:link href="{escape(a.base)}/feed{token}.xml" rel="self" type="application/rss+xml"/>']
    for dt, title, link, desc, pubdate, body in items:
        parts += ['<item>', f'<title>{escape(title)}</title>',
                  f'<link>{escape(link)}</link>',
                  f'<guid isPermaLink="true">{escape(link)}</guid>',
                  f'<pubDate>{pubdate}</pubDate>',
                  f'<description>{escape(desc)}</description>']
        if body:
            safe = body.replace(']]>', ']]]]><![CDATA[>')  # split a literal ]]> so it can't break out
            parts.append(f'<content:encoded><![CDATA[{safe}]]></content:encoded>')
        parts.append('</item>')
    parts += ['</channel>', '</rss>', '']

    out_path = os.path.join(a.out, f"feed{token}.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"OK  wrote {len(items)} item(s) -> {out_path}")
    print(f"    private feed path: /feed{token}.xml  (give Substack the FULL URL)")
    for w in warnings:
        print(f"    !! {w}")

if __name__ == "__main__":
    main()
