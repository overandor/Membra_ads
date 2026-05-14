# Vendor Strategy

Membra does not become the printer, payment processor, NFC manufacturer, or courier company. Membra is the control plane.

## Vendor roles

- Apparel and bags: Printful, Printify, Gelato.
- Stickers, decals, magnets, window clings: local sign shops, Sticker Mule-style manual workflows, or print-on-demand vendors with supported products.
- NFC and QR tags: GoToTags-style batch suppliers or partner vendors.
- Payments and payouts: Stripe Connect.
- Storage and proof files: Supabase Storage, S3, or equivalent.

## MVP vendor stack

- Database: Supabase/Postgres.
- File storage: Supabase Storage.
- Payments: Stripe Connect.
- Apparel: Printify or Printful.
- Decals/magnets/window clings: manual vendor order or local sign shop.
- NFC: batch CSV workflow.
- QR tracking: Membra redirect URLs.

## Automated v1 stack

- FastAPI/Postgres Membra backend.
- Printify adapter first for product/order automation.
- Printful adapter second for catalog/mockup/order coverage.
- Gelato adapter for global/local fulfillment.
- NFC batch adapter until a partner API is secured.
- Stripe Connect with webhook-driven payment and payout status.

## Vendor adapter interface

Each vendor adapter should implement:

```python
class VendorAdapter:
    name: str

    def validate_order(self, order): ...
    def estimate_order(self, order): ...
    def create_order(self, order): ...
    def get_order_status(self, vendor_order_id): ...
    def handle_webhook(self, payload, headers): ...
```

## Manual vendor adapter

Manual vendors are still valid in MVP. Membra should export:

- print-ready PNG/PDF/SVG
- CSV of QR/NFC IDs
- shipping labels or kit packing slips
- order manifest
- proof checklist

## NFC batch flow

1. Membra creates tag IDs.
2. Membra creates tracking URLs.
3. Membra exports CSV: tag_id, tracking_url, visible_code.
4. Vendor encodes NFC tags.
5. Vendor prints QR + visible ID.
6. Vendor ships tags.
7. Membra imports final UID/tag mapping.
8. Owner confirms receipt.
9. Tag activates only after proof review.

## Non-negotiable rule

Every physical tag must resolve to a Membra URL first. Direct advertiser URLs destroy attribution and payout proof.
