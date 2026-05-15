# MEMBRA Module Contract — Ads

## Role

Physical proof-media campaign layer for MEMBRA. Converts eligible cars, first-floor windows, stickers, signs, bags, QR/NFC surfaces, and local physical placements into advertiser-facing campaign inventory.

## System inputs

- advertiser campaign briefs
- asset/listing IDs from `Membra_kpi` or `Membra_api`
- QR/NFC artifact IDs
- proof requirements
- owner campaign acceptances
- campaign budget and creative status

## System outputs

- campaign records
- placement records
- creative approval states
- proof requirements
- advertiser KPI views
- owner payout-eligibility triggers after proof review

## Health

```text
GET /api/health
```

## Replit role

`service`

Runs as the physical-ad campaign module behind the MEMBRA OS workspace.

## Production boundary

Campaign drafts are not active placements until owner acceptance, creative approval, QR/NFC identity, proof submission, admin review, and eligibility rules are satisfied. No advertiser-performance or earnings guarantees.
