# Membra Ads API Map

Membra Ads is the master API. Frontends call Membra, and Membra calls vendor adapters behind the scenes.

## Owners

```http
POST /v1/owners
GET  /v1/owners/me
PATCH /v1/owners/me
```

## Advertisers

```http
POST /v1/advertisers
GET  /v1/advertisers/me
PATCH /v1/advertisers/me
```

## Assets and surfaces

```http
POST  /v1/ad-assets
GET   /v1/ad-assets
GET   /v1/ad-assets/{asset_id}
PATCH /v1/ad-assets/{asset_id}
POST  /v1/ad-assets/{asset_id}/verify
POST  /v1/windows
POST  /v1/vehicles
POST  /v1/wearables
POST  /v1/bags
POST  /v1/signage
```

## Campaigns

```http
POST /v1/campaigns
GET  /v1/campaigns
GET  /v1/campaigns/{campaign_id}
POST /v1/campaigns/{campaign_id}/submit-creative
POST /v1/campaigns/{campaign_id}/approve-creative
POST /v1/campaigns/{campaign_id}/fund
POST /v1/campaigns/{campaign_id}/launch
GET  /v1/campaigns/available
POST /v1/campaigns/{campaign_id}/accept
POST /v1/campaigns/{campaign_id}/decline
```

## Media kits

```http
POST /v1/media-kits
GET  /v1/media-kits/{kit_id}
POST /v1/media-kits/{kit_id}/generate-qr
POST /v1/media-kits/{kit_id}/assign-nfc
POST /v1/media-kits/{kit_id}/generate-print-files
POST /v1/media-kits/{kit_id}/order
POST /v1/media-kits/{kit_id}/confirm-receipt
POST /v1/media-kits/{kit_id}/activate
```

## Proof

```http
POST /v1/proof/photo
POST /v1/proof/location
POST /v1/proof/qr-scan
POST /v1/proof/nfc-tap
POST /v1/proof/review
GET  /v1/proof-reports/{campaign_id}
```

## Tracking redirects

```http
GET /r/{qr_id}
GET /n/{nfc_id}
```

QR and NFC tags must route through Membra first. Direct advertiser URLs break attribution, fraud checks, and payout proof.

## Payments and payouts

```http
POST /v1/stripe/connect-account
POST /v1/stripe/account-link
POST /v1/payments/create-intent
POST /v1/payments/capture
POST /v1/payouts/create-transfer
POST /v1/payouts/release
```

## Claims and disputes

```http
POST /v1/claims
GET  /v1/claims/{claim_id}
POST /v1/claims/{claim_id}/resolve
```

## Analytics

```http
GET /v1/analytics/campaign/{campaign_id}
GET /v1/analytics/owner/{owner_id}
GET /v1/analytics/asset/{asset_id}
```

## Webhooks

```http
POST /v1/webhooks/stripe
POST /v1/webhooks/printful
POST /v1/webhooks/printify
POST /v1/webhooks/gelato
POST /v1/webhooks/nfc-vendor
```

All webhooks must be signature-verified where the vendor supports signatures.
