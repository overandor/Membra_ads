# Membra Ads

Membra Ads is the physical proof media layer of MEMBRA: a verified micro-out-of-home advertising network where everyday owners can monetize cars, windows, shirts, bags, stickers, NFC tags, and other real-world surfaces.

## One-line thesis

Membra turns real-world surfaces into verified ad inventory with QR/NFC attribution, proof photos, campaign funding, vendor-fulfilled media kits, and owner payouts.

## Product category

- Physical micro-ad network
- QR/NFC proof media API
- Owner monetization marketplace
- Advertiser campaign fulfillment layer
- ProofBook-backed out-of-home attribution system

## Core participants

- **Owner** — person who owns an ad surface such as a car, window, shirt, bag, or physical location.
- **Advertiser** — business funding a physical placement campaign.
- **Campaign** — funded ad offer with creative, destination, budget, placement requirements, and proof rules.
- **Media Kit** — QR/NFC/print package produced for a campaign placement.
- **Proof Reviewer** — human or automated reviewer that verifies installation, location, timestamp, and compliance.
- **Vendor** — Printful, Printify, Gelato, local sign shop, Sticker Mule-style manual workflow, or NFC tag supplier.

## Membra control-plane rule

The frontend, owner app, advertiser dashboard, and admin dashboard call only Membra APIs.

Vendor APIs sit behind Membra as fulfillment rails. Owners and advertisers should never call Printful, Printify, Gelato, Stripe, or NFC vendors directly.

## MVP flow

1. Owner registers a surface.
2. Advertiser creates a campaign.
3. Advertiser submits creative.
4. Admin approves creative.
5. Advertiser funds campaign.
6. Owner accepts campaign.
7. Membra generates QR tracking URL and optional NFC ID.
8. Membra creates a media kit.
9. Membra orders the kit or exports vendor-ready files.
10. Owner confirms receipt.
11. Owner uploads proof photo and location.
12. Membra reviews proof.
13. QR/NFC scans are tracked through Membra redirect URLs.
14. Stripe Connect payout is released when proof rules pass.

## Payout law

No approved creative -> no kit generated.

No Membra QR/NFC ID -> no certified placement.

No shipped kit -> no activation.

No proof photo + timestamp + location match -> no payout eligibility.

No Membra redirect URL -> no scan attribution.

No approved proof -> no payout release.

## Repository contents

- `app.py` — FastAPI starter control plane.
- `schema.sql` — Postgres/Supabase-ready schema.
- `.env.example` — configuration scaffold.
- `docs/api-map.md` — canonical endpoint map.
- `docs/vendor-strategy.md` — Printful/Printify/Gelato/NFC/manual vendor strategy.
- `docs/proof-policy.md` — proof, fraud, review, and payout rules.
- `docs/pricing.md` — starting campaign and payout model.

## Safety and compliance posture

This repository does not execute payments by itself. Payment capture and payout release must be implemented through Stripe Connect or another regulated payment rail.

This repository does not imply guaranteed owner income or guaranteed advertiser performance.

All physical placements require advertiser approval, owner consent, proof review, and audit logging.

## Current stage

Productized seed repo. Backend scaffold and documentation are ready for MVP implementation.
