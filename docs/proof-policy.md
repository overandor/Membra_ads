# Proof and Payout Policy

Membra Ads pays owners only when campaign proof passes review.

## Proof objects

A proof event should include:

- proof_id
- campaign_id
- owner_id
- asset_id
- media_kit_id
- proof_type
- photo_url or evidence_url
- latitude and longitude when permitted
- timestamp
- device metadata hash
- reviewer_id
- review_status
- rejection_reason
- created_at

## Required proof types

- receipt proof: owner confirms kit arrival.
- install proof: owner proves media is installed.
- location proof: owner confirms approved placement area.
- scan proof: QR scan passes through Membra redirect.
- tap proof: NFC tap passes through Membra redirect.
- maintenance proof: recurring proof for longer campaigns.

## Review states

```text
submitted
auto_checked
needs_review
approved
rejected
disputed
```

## Campaign activation rule

A campaign placement becomes active only when:

1. creative is approved
2. campaign is funded
3. media kit has Membra QR/NFC identity
4. kit is shipped or generated
5. owner confirms receipt
6. install proof is approved

## Payout eligibility rule

Owner payout becomes eligible only when:

1. placement is active
2. proof photo passes review
3. timestamp is inside campaign window
4. location is inside allowed placement zone when GPS is required
5. QR/NFC tracking URL belongs to Membra
6. no unresolved fraud alert exists

## Fraud flags

- reused proof photo
- mismatched campaign creative
- missing QR/NFC code
- geofence mismatch
- timestamp outside campaign window
- suspicious scan clustering
- owner self-scanning pattern
- blocked advertiser category
- vehicle/window/wearable asset not verified

## Payout states

```text
pending
eligible
held
released
failed
reversed
```

## ProofBook bridge

Every important proof event should create a ProofBook record:

```text
canonical JSON -> SHA-256 hash -> optional Devnet anchor -> database signature record
```

## Safety line

Membra must never promise guaranteed owner income or guaranteed advertiser results. It sells verified media placement, attribution, and proof-based payout infrastructure.
