# executivestandard.csexecutiveservices-website

Source for executivestandard.csexecutiveservices.com — The Executive Standard, Corey Sheldon's editorial series for CS Executive Services, LLC. Also mirrored to Substack.

## Repository layout

```
*.html                  Static site — one file per post (served by nginx from
                         /var/www/executivestandard.csexecutiveservices.com)
_md/                     Markdown source for each post (title/description/date/
                         source frontmatter + body), predates the .html render
assets/                  Wordmark, icons
icons/                   Favicon, apple-touch-icon
keys/                    Public keys for the shared trust root (see Brand and
                         security notes below) — same files as the apex repo,
                         copied intentionally
security/
  signing.env.example    Template — copy to signing.env, fill in fingerprint
  signing.env            (gitignored) Real fingerprint, never committed
  trusted-signing-key.pub.asc   Exported public half of the signing key
scripts/
  sign-manifest.sh       Hashes + GPG-signs the whole repo tree
  verify-manifest.sh     Verifies MANIFEST.sha256(.asc) against the trusted key
MANIFEST.sha256          Generated — sha256 of every tracked/untracked file
MANIFEST.sha256.asc      Generated — detached GPG signature over the manifest
manifest.json            PWA manifest
sw.js                    Service worker
sitemap.xml / robots.txt / llms.txt / llm.txt
```

## Deployment (Pi 5)

Unlike the apex site, this repo has no build step and no contact-api backend — pages are static HTML, hand-authored or generated per post, and served directly.

```bash
# Deploy static site
sudo mkdir -p /var/www/executivestandard.csexecutiveservices.com
sudo cp -r ./*.html assets icons manifest.json sw.js sitemap.xml robots.txt \
    llms.txt llm.txt /var/www/executivestandard.csexecutiveservices.com/
sudo chown -R nginx:nginx /var/www/executivestandard.csexecutiveservices.com
sudo nginx -t && sudo systemctl reload nginx
```

Cloudflare tunnel route (dashboard):

```
executivestandard.csexecutiveservices.com → http://127.0.0.1:80
```

## Publishing a new post

1. Draft the post as markdown in `_md/<slug>.md` (frontmatter: `title`, `description`, `date`, `source`).
2. Build the `.html` page from an existing post as a template — same masthead, styles, and archive-list chrome, article body replaced.
3. Add the new post to the "More memos" archive-list block on every other `.html` page that carries one.
4. Run `scripts/sign-manifest.sh`, verify with `scripts/verify-manifest.sh`, commit, push.

## Signed manifest integrity

Every file in the repo — tracked or untracked-but-not-ignored — is hashed into `MANIFEST.sha256` and detached-signed into `MANIFEST.sha256.asc` using the same GPG identity that signs the apex site and other platform work (`security/trusted-signing-key.pub.asc`, fingerprint in `security/signing.env`, gitignored).

```bash
scripts/sign-manifest.sh      # deliberate, human-run — prompts for GPG passphrase
scripts/verify-manifest.sh    # checks signature + full-tree hash match
```

Exit 0 from `verify-manifest.sh` means the working tree matches exactly what was signed. Any non-zero exit means don't trust it. This is the same mechanism used by `csexecutiveservices-website` and `ctdi-dispatch-internal` — one shared root of trust across properties, separate manifests and repos per property.

## Brand

| Token          | Light      | Dark       |
|----------------|------------|------------|
| Background     | `#F3EFE5`  | `#0a1628`  |
| Surface        | `#FFFFFF`  | `#13233d`  |
| Ink            | `#0a1628`  | `#eef1f4`  |
| Ink (soft)     | `#13233d`  | `#b8c2cc`  |
| Muted          | `#6b7c8d`  | `#6b7c8d`  |
| Rule           | `#E1DACB`  | `#0d1e35`  |
| Accent         | `#c4881e`  | `#e8a124`  |

| Role           | Font              |
|----------------|-------------------|
| Headlines      | Fraunces          |
| Body           | Newsreader        |
| Kicker/mono UI | IBM Plex Mono     |
