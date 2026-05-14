# Membra Ads

**Membra Ads is the first commercial wedge of MEMBRA Labs and the MEMBRA Proof Network.**

It turns physical surfaces into verified QR/NFC media inventory with campaign funding, proof review, scan/tap attribution, audit records, and payout eligibility.

## Company Context

- Company: **MEMBRA Labs**
- Flagship product: **MEMBRA Proof Network**
- Commercial wedge: **Membra Ads**
- Category: verified physical media, proof-backed micro-out-of-home advertising, QR/NFC attribution

Membra Ads is not a standalone ad network. It is the campaign and proof-control plane for MEMBRA Labs.

## Core Workflow

1. Owner registers a physical surface or asset.
2. Advertiser creates a campaign.
3. Advertiser submits destination and budget.
4. MEMBRA generates QR/NFC media kit identifiers.
5. Owner receives or installs the media kit.
6. Owner submits proof photo and optional location data.
7. Admin or automated review approves, rejects, or disputes proof.
8. QR/NFC scans route through MEMBRA-controlled tracking URLs.
9. Payout eligibility is calculated only after proof rules pass.
10. Reports flow into MEMBRA KPI and ProofBook.

## Current Repository Contents

- `app.py` — FastAPI scaffold for owners, advertisers, assets, campaigns, media kits, proof events, QR redirects, NFC tracking, and audit events.
- `schema.sql` — database schema scaffold, where present.
- `.env.example` — environment configuration scaffold, where present.
- `docs/` — product, proof, pricing, API, and vendor strategy documentation, where present.

## API Scope

This repo owns the first product backend for:

- owner creation
- advertiser creation
- ad asset registration
- asset verification
- campaign creation
- campaign funded status
- media kit generation
- QR/NFC ID generation
- proof submission
- proof review
- redirect tracking
- audit event generation

## Safety and Commercial Rules

- No approved creative → no certified kit.
- No MEMBRA QR/NFC ID → no certified placement.
- No proof photo/timestamp/location check → no payout eligibility.
- No MEMBRA redirect URL → no scan attribution.
- No approved proof → no payout release.
- No guaranteed advertiser performance.
- No guaranteed owner income.

## Relationship to Other Repos

| Repo | Relationship |
|---|---|
| `overandor/membra` | company hub, demo runtime, doctrine, appraisal, KPI generator |
| `overandor/membra-qr-gateway` | buyer-visible dashboard and QR/provenance UI |
| `overandor/Membra_kpi` | reports for campaigns, owners, advertisers, proof, scans, and payouts |
| `overandor/Membra_proofbook` | future proof ledger for hashes, audit records, and eligibility states |
| `overandor/Membra_vendor_adapters` | future vendor rails for print, stickers, NFC, and fulfillment |
| `overandor/Membra_admin-` | future operator console for creative approval, proof review, fraud, claims, payouts |
| `overandor/Membra_wallet` | optional non-custodial payout and wallet relay boundary |

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic
uvicorn app:app --reload
```

Health check:

```text
GET /v1/health
```

## Productization Priority

This repo should become the first production backend for MEMBRA Labs.

Next build steps:

1. add proper auth
2. move SQLite to Postgres/Supabase
3. add API docs and tests
4. connect seeded demo data
5. connect dashboard panels from `membra-qr-gateway`
6. add proof-photo upload storage
7. add payout hold/release state machine
8. expose KPI/reporting hooks

## Status

Prototype backend scaffold. Suitable for demo consolidation, not yet production deployment without auth, persistence hardening, tests, and compliance review.