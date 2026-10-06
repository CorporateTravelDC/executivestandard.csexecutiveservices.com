#!/usr/bin/env bash
# executivestandard-publish.sh
#
# Reusable publisher for The Executive Standard blog. Takes any article
# markdown file (with YAML-ish frontmatter: title, kicker, date, slug,
# excerpt/description), converts it to the site's HTML template, adds it
# to the "More memos" archive list on every other page, copies the site
# into the versioned repo, signs the manifest, commits, and pushes.
#
# Usage:
#   executivestandard-publish.sh <article.md>
#
# The markdown file may live anywhere; it does not need to already be in
# _md/. It gets copied into _md/<slug>.md as part of the run.
#
# Expected frontmatter (YAML-ish, between --- lines at the top):
#   title: "Article Title"
#   kicker: "Desk Memo"                  # optional, defaults to "Desk Memo"
#   date: 2026-09-09                     # required, YYYY-MM-DD
#   slug: "article-slug"                 # optional, defaults to the
#                                         # input filename's stem
#   excerpt: "One-line dek / archive summary."
#     (description: also accepted as an alias for excerpt)
#
# Everything after the closing --- is treated as the article body in
# Markdown: ## / ### headers, **bold**, *italic*, [text](url) links,
# "- " unordered lists, and blank-line-separated paragraphs.
#
# Run from anywhere; SITE_DIR and REPO_DIR below are the two paths that
# matter and can be overridden via environment variables if needed.
set -euo pipefail

SITE_DIR="${SITE_DIR:-/var/www/executivestandard.csexecutiveservices.com}"
REPO_DIR="${REPO_DIR:-/opt/corporatetraveldc/private/executivestandard-website}"
TEMPLATE="${TEMPLATE:-the-squeeze-isnt-the-goal-its-the.html}"

if [[ $# -ne 1 ]]; then
    echo "Usage: $(basename "$0") <article.md>" >&2
    exit 1
fi

INPUT_MD="$1"
if [[ ! -f "${INPUT_MD}" ]]; then
    echo "XX ${INPUT_MD} not found." >&2
    exit 1
fi

if [[ ! -f "${SITE_DIR}/${TEMPLATE}" ]]; then
    echo "XX Template ${TEMPLATE} not found in ${SITE_DIR} -- aborting." >&2
    exit 1
fi

if [[ ! -d "${REPO_DIR}" ]]; then
    echo "XX ${REPO_DIR} not found -- repo not set up? aborting." >&2
    exit 1
fi

echo "[1/5] Parsing frontmatter and converting Markdown to HTML..."

# The python helper does the real work: parse frontmatter, convert the
# body, clone the template, write <slug>.html, and emit the resolved
# slug/date/title/excerpt on stdout (one per line) so bash can pick them
# up for the archive-list and git steps below.
RESULT="$(python3 - "${INPUT_MD}" "${SITE_DIR}" "${TEMPLATE}" << 'PYEOF'
import sys, re, os
from datetime import datetime

input_md, site_dir, template_name = sys.argv[1], sys.argv[2], sys.argv[3]

with open(input_md, "r", encoding="utf-8") as f:
    raw = f.read()

# --- Frontmatter parsing -------------------------------------------------
m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
if not m:
    print("XX No YAML frontmatter (---...---) found at the top of the file.", file=sys.stderr)
    sys.exit(2)

fm_raw, body_md = m.group(1), m.group(2)

fm = {}
for line in fm_raw.splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if ":" not in line:
        continue
    key, _, value = line.partition(":")
    key = key.strip().lower()
    value = value.strip()
    # strip a single layer of surrounding quotes, if present
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    fm[key] = value

title = fm.get("title")
if not title:
    print("XX frontmatter is missing 'title'.", file=sys.stderr)
    sys.exit(2)

kicker = fm.get("kicker", "Desk Memo")
date_raw = fm.get("date")
if not date_raw:
    print("XX frontmatter is missing 'date' (expected YYYY-MM-DD).", file=sys.stderr)
    sys.exit(2)
date_obj = datetime.strptime(date_raw[:10], "%Y-%m-%d")
date_long = date_obj.strftime("%B %-d, %Y")
date_short = date_obj.strftime("%b %-d")

slug = fm.get("slug") or os.path.splitext(os.path.basename(input_md))[0]

excerpt = fm.get("excerpt") or fm.get("description") or ""

byline_name = fm.get("author") or fm.get("byline") or "Corey Sheldon"

# --- Markdown body -> HTML (minimal, self-contained) ---------------------
def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def inline(s):
    # links first, so bracket/paren contents don't get chewed by bold/italic
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    return s

lines = body_md.splitlines()
html_parts = []
i = 0
list_buffer = []

def flush_list():
    if list_buffer:
        html_parts.append("<ul>")
        for item in list_buffer:
            html_parts.append(f"<li>{inline(escape(item))}</li>")
        html_parts.append("</ul>")
        list_buffer.clear()

paragraph_buffer = []

def flush_paragraph():
    if paragraph_buffer:
        text = " ".join(paragraph_buffer).strip()
        if text:
            html_parts.append(f"<p>{inline(escape(text))}</p>")
        paragraph_buffer.clear()

while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    if not stripped:
        flush_paragraph()
        flush_list()
        i += 1
        continue

    h = re.match(r"^(#{1,4})\s+(.*)$", stripped)
    if h:
        flush_paragraph()
        flush_list()
        level = min(len(h.group(1)) + 1, 4)  # article's # -> site's h2
        text = h.group(2)
        html_parts.append(f"<h{level}>{inline(escape(text))}</h{level}>")
        i += 1
        continue

    if re.match(r"^[-*]\s+", stripped):
        flush_paragraph()
        item_text = re.sub(r"^[-*]\s+", "", stripped)
        list_buffer.append(item_text)
        i += 1
        continue

    flush_list()
    paragraph_buffer.append(stripped)
    i += 1

flush_paragraph()
flush_list()

body_html = "\n".join(html_parts)

# --- Clone template --------------------------------------------------------
template_path = os.path.join(site_dir, template_name)
with open(template_path, "r", encoding="utf-8") as f:
    template = f.read()

template = re.sub(
    r"<title>.*?</title>",
    f"<title>{escape(title)} \u2014 The Executive Standard</title>",
    template, count=1,
)

new_article = f'''<article>
  <p class="kicker">{escape(kicker)}</p>
  <h1 class="headline">{escape(title)}</h1>
  <p class="dek">{inline(escape(excerpt))}</p>
  <div class="byline">
    <span class="name">{escape(byline_name)}</span>
    <span class="sep">&middot;</span>
    <span>{date_long}</span>
  </div>

  <div class="prose">
{body_html}
  </div>
</article>'''

template = re.sub(r"<article>.*?</article>", lambda _: new_article, template, count=1, flags=re.DOTALL)

out_path = os.path.join(site_dir, f"{slug}.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(template)

# --- Save/refresh the _md source alongside it -------------------------------
md_dir = os.path.join(site_dir, "_md")
os.makedirs(md_dir, exist_ok=True)
md_out_path = os.path.join(md_dir, f"{slug}.md")
if os.path.abspath(md_out_path) != os.path.abspath(input_md):
    with open(md_out_path, "w", encoding="utf-8") as f:
        f.write(raw)

# hand results back to bash
print(slug)
print(date_short)
print(title)
print(excerpt)
PYEOF
)"

# read the four lines the python helper printed
SLUG="$(sed -n '1p' <<< "${RESULT}")"
DATE_SHORT="$(sed -n '2p' <<< "${RESULT}")"
TITLE="$(sed -n '3p' <<< "${RESULT}")"
EXCERPT="$(sed -n '4p' <<< "${RESULT}")"

echo "  wrote ${SLUG}.html (${TITLE})"

echo "[2/5] Adding archive-list entry to every other page..."

cd "${SITE_DIR}"
python3 - "${SLUG}" "${DATE_SHORT}" "${TITLE}" "${EXCERPT}" << 'PYEOF'
import sys, glob

slug, date_short, title, excerpt = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

new_item = f'''    <a href="/{slug}.html" class="archive-item">
      <span class="date">{date_short}</span>
      <span>
        <p class="title">{escape(title)}</p>
        <p class="excerpt">{escape(excerpt)}</p>
      </span>
    </a>
'''

files = [f for f in glob.glob("*.html") if f != f"{slug}.html"]
changed = 0
for fname in files:
    with open(fname, "r", encoding="utf-8") as f:
        content = f.read()
    if f"{slug}.html" in content:
        continue
    if '<div class="archive-list">' not in content:
        continue
    content = content.replace(
        '<div class="archive-list">',
        '<div class="archive-list">\n' + new_item,
        1,
    )
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    changed += 1

print(f"  updated {changed} files")
PYEOF

echo "[3/5] Copying site into versioned repo..."
cp -r "${SITE_DIR}"/*.html "${REPO_DIR}/"
mkdir -p "${REPO_DIR}/_md"
cp "${SITE_DIR}/_md/${SLUG}.md" "${REPO_DIR}/_md/"

echo "[4/5] Signing manifest (you'll be prompted for your GPG passphrase)..."
cd "${REPO_DIR}"
scripts/sign-manifest.sh

echo "[5/5] Committing and pushing..."
git add -A
git commit -m "Add: ${TITLE}"
git push

echo ""
echo "Done. Live at: https://executivestandard.csexecutiveservices.com/${SLUG}.html"
