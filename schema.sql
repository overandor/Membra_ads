-- Membra Ads compact MVP schema

CREATE TABLE IF NOT EXISTS owners (
  id TEXT PRIMARY KEY,
  email TEXT,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS advertisers (
  id TEXT PRIMARY KEY,
  email TEXT,
  company_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ad_assets (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  title TEXT NOT NULL,
  city TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
  id TEXT PRIMARY KEY,
  advertiser_id TEXT NOT NULL,
  title TEXT NOT NULL,
  destination_url TEXT NOT NULL,
  budget_cents INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS media_kits (
  id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  asset_id TEXT,
  kit_type TEXT NOT NULL,
  qr_id TEXT,
  nfc_id TEXT,
  vendor TEXT,
  vendor_order_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proof_events (
  id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  owner_id TEXT,
  asset_id TEXT,
  media_kit_id TEXT,
  proof_type TEXT NOT NULL,
  evidence_url TEXT,
  latitude REAL,
  longitude REAL,
  status TEXT NOT NULL DEFAULT 'submitted',
  review_notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracking_events (
  id TEXT PRIMARY KEY,
  campaign_id TEXT,
  qr_id TEXT,
  nfc_id TEXT,
  event_type TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  actor_id TEXT,
  event_type TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL
);
