# Publishing pipeline — file convention (read me)

Per operator note 2026-09-28. Applies to every Executive Standard artifact staged here.

## Which file the pipeline uses
- **`articles/<slug>.md` is the source of truth** (2026-10-03: moved from the repo root;
  every article -- Pi-native, Substack-era, and override-patched -- now lives here, one
  file each, canonical frontmatter `title / dek / date / kicker`, UNQUOTED values: the
  sync's frontmatter parser is a plain `key: value` splitter and would keep literal
  quotes). The publication pipeline (`executive_standard_sync.py` in the dispatch repo)
  reads THIS directory and renders the HTML itself. `gated: true` keeps an article
  members-only on the public transparency sibling (hash published, text not); writing
  "members only" anywhere in the frontmatter is treated as the same flag.
- **`<slug>.html` is a visual preview only.** It is the fully-styled brand page so you can
  see exactly how it will render (the "viewport"). **It deliberately has NO inline front
  matter** — the YAML block was stripped because it does not parse cleanly when the file is
  moved over and the pipeline generates HTML from the `.md` regardless. Do not feed the HTML
  to the pipeline; keep it as reference.
- **`<slug>-substack.md` is the Substack paste version.** Fixed Substack structure
  (title + subtitle → "Originally published at" callout → teaser first paragraph →
  subscription blurb → ▶ PAYWALL → body → subscribe block). For hand-pasting into Substack
  at T0, not for the blog pipeline.

## Cadence (unchanged, per executive-standard-publishing-standard)
Blog (`<slug>.md`) at T−24h → Substack paid (`<slug>-substack.md`) +24h → free unlock +7d.
Front matter is `evergreen: true` and dated first-publication; not time-locked.

## This batch (staged 2026-09-28, ready to publish)
- `the-landing-that-never-happened` — audit-trail / decision-provenance proof. Follow-on to "The New Hire."
- `default-on-is-not-consent` — silent-sync / sovereignty proof. Companion to "The New Hire." Names Claude Code / Anthropic per the series discretion standard, as a fair field report; spine verified against the vendor's live docs.
