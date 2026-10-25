#!/usr/bin/env python3
"""refresh-private-feed.py — regenerate the Substack private feed, then prove it.

Final step of executivestandard-publish.sh (2026-10-24, operator); also safe to
run on its own. Builds the feed from <site>/_md with the members host as base,
the way the live feed has always been built.

Item bodies are the abridged Substack edition (substack/<slug>-substack.md in
this repo; every Substack copy lives there, apart from the blog's _md/) where
one exists, the full article otherwise; the generator's output lists which.

Two modes:
  --slug SLUG   the publish mode: the feed carries ONLY that article. Substack's
                importer adds every item it does not already hold, and a post
                imported and then deleted can come back, so a one-article feed
                is the only way an import brings in exactly the new post.
                Check: exactly one item, and it is SLUG.
  (no --slug)   the full archive feed. Check: no guid in the previous feed has
                disappeared or changed (Substack keys on the guid).
Either way the new feed must parse; any failure exits 1.

The token is read from config.json and never printed: the generator's
"private feed path" line is dropped, the token is masked in every other line it
prints, and the feed is found by its exact name.

Usage:
    scripts/refresh-private-feed.py [--slug SLUG]
        [--site /var/www/executivestandard.csexecutiveservices.com]
        [--config config.json]
        [--base https://members.executivestandard.csexecutiveservices.com]
"""
import argparse, json, os, subprocess, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def token_of(cfg):
    with open(cfg, encoding="utf-8") as f:
        tok = (json.load(f).get("SECRET_RSS_TOKEN") or "").strip()
    if not tok or tok.startswith("REPLACE_"):
        sys.exit("XX private feed: SECRET_RSS_TOKEN missing/placeholder in config.json")
    return tok


def items_of(path):
    return ET.parse(path).getroot().findall("./channel/item")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="")
    ap.add_argument("--site", default="/var/www/executivestandard.csexecutiveservices.com")
    ap.add_argument("--config", default=os.path.join(REPO, "config.json"))
    ap.add_argument("--base", default=os.environ.get(
        "EXEC_STANDARD_FEED_BASE", "https://members.executivestandard.csexecutiveservices.com"))
    a = ap.parse_args()

    tok = token_of(a.config)
    feed = os.path.join(a.site, f"feed{tok}.xml")
    before = {}
    if os.path.isfile(feed):
        before = {i.findtext("guid"): i.findtext("title") for i in items_of(feed)}

    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "generate-private-feed.py"),
         "--config", a.config, "--md", os.path.join(a.site, "_md"),
         "--html", a.site, "--out", a.site, "--base", a.base,
         "--editions", os.path.join(REPO, "substack")]
        + (["--only", a.slug] if a.slug else []),
        capture_output=True, text=True)
    for line in (r.stdout + r.stderr).splitlines():
        if "private feed path" in line or "no status:/draft:" in line:
            continue                      # token line / known noise
        print("    " + line.strip().replace(tok, "<token>"))   # the generator's "wrote ->" line carries the path
    if r.returncode != 0:
        sys.exit(f"XX private feed: generator failed (rc={r.returncode})")

    try:
        after = items_of(feed)
    except (OSError, ET.ParseError) as e:
        sys.exit(f"XX private feed: new feed unreadable ({type(e).__name__})")
    if not after:
        sys.exit("XX private feed: new feed has no items")
    guids = {i.findtext("guid") for i in after}

    if a.slug:
        if len(after) != 1 or not after[0].findtext("guid").rstrip("/").endswith(f"/{a.slug}.html"):
            sys.exit(f"XX private feed: expected exactly {a.slug}, got {len(after)} item(s)")
        print(f"OK  private feed: 1 item -- {after[0].findtext('title')}")
    else:
        lost = sorted(g for g in before if g not in guids)
        if lost:
            print("XX private feed: these items lost their guid; Substack would re-import them:", file=sys.stderr)
            for g in lost:
                print(f"     {before[g]}  ({g})", file=sys.stderr)
            sys.exit(1)
        added = [i.findtext("title") for i in after if i.findtext("guid") not in before]
        print(f"OK  private feed: {len(after)} items ({len(after) - len(added)} unchanged guids, "
              f"{len(added)} new); newest: {after[0].findtext('title')}")
        for t in added:
            print(f"    new in feed: {t}")

    print("""    Substack: Settings > Import/Export > Import posts > paste the full feed URL > Get started
      [ ] Imported posts available only for paying subscribers   <- UNCHECKED: free to everyone
      [ ] Update existing posts   <- UNCHECKED (it overwrites posts already on Substack)
    Posts land published, with no email sent.""")


if __name__ == "__main__":
    main()
