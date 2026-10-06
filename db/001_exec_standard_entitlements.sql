-- Executive Standard entitlements control plane (2026-09-27).
-- Self-owned readership/access table -- grants come from any source (Substack,
-- Patreon, LinkedIn promos, direct, collaborator comps), each TAGGED with its
-- source, all counted/capped/revocable here without touching Substack itself.
-- Lives in the corporatetraveldc Postgres, gated like the demo DB.

CREATE TABLE IF NOT EXISTS exec_standard_sources (
    source   TEXT PRIMARY KEY,
    enabled  BOOLEAN NOT NULL DEFAULT true,   -- flip false = stop granting, live
    cap      INTEGER,                          -- max grants (NULL = unlimited)
    label    TEXT,
    notes    TEXT
);

CREATE TABLE IF NOT EXISTS exec_standard_tokens (
    token       TEXT PRIMARY KEY,              -- opaque random, the access value
    email       TEXT,                          -- who (nullable for anon promos)
    source      TEXT NOT NULL REFERENCES exec_standard_sources(source),
    campaign    TEXT,                          -- optional named batch ("linkedin-25-free")
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ,                   -- NULL = no expiry
    status      TEXT NOT NULL DEFAULT 'active',-- active | revoked
    redeemed_at TIMESTAMPTZ,                   -- first activation ("the run") + time
    last_seen   TIMESTAMPTZ,                   -- ongoing use
    notes       TEXT
);
CREATE INDEX IF NOT EXISTS idx_es_tokens_email    ON exec_standard_tokens(email);
CREATE INDEX IF NOT EXISTS idx_es_tokens_source   ON exec_standard_tokens(source, status);
CREATE INDEX IF NOT EXISTS idx_es_tokens_campaign ON exec_standard_tokens(campaign);

-- Seed sources. Active = the live grant channels; collab-* are stubbed
-- (disabled) comp/collaborator segments to switch on per collaboration.
INSERT INTO exec_standard_sources (source, enabled, cap, label, notes) VALUES
  ('substack-seed',   true,  NULL, 'Substack — seeded existing subscribers', 'On Substack before the self-host migration'),
  ('substack-direct', true,  NULL, 'Substack — post-migration',              'New Substack signups going forward'),
  ('linkedin',        true,  NULL, 'LinkedIn',                               'LinkedIn teasers / follower promos'),
  ('patreon',         true,  NULL, 'Patreon',                                'Patreon supporters'),
  ('collab-youtube',          false, NULL, 'Collaborator — YouTube creator',          'Comp/collaborator perk (segment)'),
  ('collab-substack-creator', false, NULL, 'Collaborator — Substack creator',         'Comp/collaborator perk (segment)'),
  ('collab-linkedin-creator', false, NULL, 'Collaborator — LinkedIn premium creator', 'Comp/collaborator perk (segment)'),
  ('collab-blog',             false, NULL, 'Collaborator — outside blog / back-ref',  'Comp/collaborator perk (segment)'),
  ('collab-comp',             false, NULL, 'Collaborator — general comp',             'Catch-all comp collaborator')
ON CONFLICT (source) DO NOTHING;
