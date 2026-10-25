#!/usr/bin/env python3
"""generate-private-feed.py — build the tokenised private RSS feed.

This is the point of the Executive Standard lockdown: a secret feed at
    /feed<SECRET_RSS_TOKEN>.xml
that ONLY Substack's Private-Mode RSS importer (holding the token path) can
pull. The middleware / nginx gate serve this exact path and suppress every
ordinary /feed probe.

What Substack's importer actually does (2026-10-24, verified on a real import
and against its help page): it is run by hand (Settings > Import/Export >
Import posts), it adds every item it does not already hold (an item it holds
is skipped; one imported and then deleted may come back), imported posts land
PUBLISHED, not as drafts, and the only paywall control is "available only for
paying subscribers" for the whole post. "Update existing posts" overwrites
posts already on Substack with the feed version: leave it unchecked. Hence
--only: the publish step feeds Substack the one new article and nothing else.

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

def _inline(s):
    # same rules as executivestandard-publish.sh's converter: links first,
    # then bold, then italic
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    return s

# Operator template, 2026-10-24 (the hand-edited "Right Model, Right Task"):
# Substack's own title/subtitle fields carry the H1 and the bold dek, the
# paywall-era "Subscribers read the full piece below." goes (the rest of that
# line stays), the bottom "**Subscribe**" goes (Substack shows its button),
# "This is the abridged edition." stays, and links to an article on the
# members host point at its .html page.
_PITCH = re.compile(r"\s*Subscribers read the full (?:piece|note) below\.")
_MEMBERS_SLUG = re.compile(
    r"(https://members\.executivestandard\.csexecutiveservices\.com/[a-z0-9-]+)\)")

def _strip_pitch(line):
    """Apply the template to one line; None when nothing is left of it."""
    t = line.strip()
    if re.fullmatch(r"\*\*Subscribe\*\*", t):
        return None
    line = _MEMBERS_SLUG.sub(r"\1.html)", line)
    if not _PITCH.search(line):
        return line
    t = _PITCH.sub("", line.strip()).strip()
    m = re.fullmatch(r"(\*{1,2})\s*(.*?)\s*(\*{1,2})", t)
    if m and m.group(1) == m.group(3):
        t = f"{m.group(1)}{m.group(2)}{m.group(3)}" if m.group(2) else ""
    return t if re.search(r"\w", t) else None

def render_edition(path):
    """<slug>-substack.md -> HTML: the publish script's Markdown rules plus
    '> ' blockquotes and '---' rules, which the editions use. The leading
    '# Title', staging notes (<!-- -->) and the '▶ PAYWALL' marker line are
    dropped: the item carries the title, and Substack runs no paywall."""
    with open(path, encoding="utf-8") as f:
        # staging notes (<!-- ... -->) never reach Substack
        lines = re.sub(r"<!--.*?-->", "", f.read(), flags=re.S).splitlines()
    # 2026-10-24 (operator): Substack runs the abridged editions with no
    # paywall, so the "▶ PAYWALL ..." marker line is dropped, not rendered.
    lines = [l for l in lines if not re.match(r"^\W*▶\s*PAYWALL", l.strip())]
    # operator template (see _strip_pitch)
    lines = [_strip_pitch(l) for l in lines]
    lines = [l for l in lines if l is not None]
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^#\s+", lines[0]):
        lines.pop(0)
        # the bold dek right under the title is Substack's subtitle, not body
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and re.fullmatch(r"\*\*[^*].*\*\*", lines[0].strip()):
            lines.pop(0)
    out, para, items, quote = [], [], [], []
    def flush():
        if para:
            out.append(f"<p>{_inline(escape(' '.join(para)))}</p>"); para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{_inline(escape(i))}</li>" for i in items) + "</ul>"); items.clear()
        if quote:
            out.append(f"<blockquote><p>{_inline(escape(' '.join(quote)))}</p></blockquote>"); quote.clear()
    for line in lines:
        t = line.strip()
        if not t:
            flush(); continue
        h = re.match(r"^(#{1,4})\s+(.*)$", t)
        if h:
            flush()
            lvl = min(len(h.group(1)) + 1, 4)
            out.append(f"<h{lvl}>{_inline(escape(h.group(2)))}</h{lvl}>"); continue
        if re.fullmatch(r"-{3,}|\*{3,}", t):
            flush(); out.append("<hr>"); continue
        if t.startswith(">"):
            if para or items: flush()
            quote.append(t.lstrip(">").strip()); continue
        if re.match(r"^[-*]\s+", t):
            if para or quote: flush()
            items.append(re.sub(r"^[-*]\s+", "", t)); continue
        if items or quote: flush()
        para.append(t)
    flush()
    return "\n".join(out)

def find_edition(dirs, slug):
    for d in dirs:
        p = os.path.join(d, f"{slug}-substack.md")
        if os.path.isfile(p):
            return p
    return None

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
    # 2026-10-24: Substack's importer adds every feed item it doesn't already
    # hold, including posts that were imported and then deleted. A feed that
    # carries only the article just published can never bring anything else
    # back. Repeatable; omit for the full archive feed.
    ap.add_argument("--only", action="append", default=[], metavar="SLUG")
    # 2026-10-24 (operator): Substack gets the abridged Substack edition
    # (<slug>-substack.md: teaser, PAYWALL marker, body) where one exists,
    # searched in these directories in order; the full article otherwise.
    ap.add_argument("--editions", action="append", default=[], metavar="DIR")
    a = ap.parse_args()

    token = load_token(a.config)
    items, warnings, used_edition, full_copy = [], [], [], []
    for fn in sorted(os.listdir(a.md)):
        if not fn.endswith(".md"): continue
        if fn == "index.md" or fn.startswith("teaser-"): continue
        slug = fn[:-3]
        if a.only and slug not in a.only:
            continue
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
        edition = find_edition(a.editions, slug) if a.editions else None
        if edition:
            body = render_edition(edition)
            used_edition.append(slug)
        else:
            body = article_html(a.html, slug)
            if a.editions:
                full_copy.append(slug)
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
    if a.editions:
        print(f"    Substack editions: {len(used_edition)}; full article (no -substack.md): {len(full_copy)}")
        for s_ in full_copy:
            print(f"    full article: {s_}")
    for w in warnings:
        print(f"    !! {w}")

if __name__ == "__main__":
    main()
