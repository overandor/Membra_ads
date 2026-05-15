"""MEMBRA Ads — physical proof media control plane for Hugging Face/FastAPI.

Production posture:
- deterministic campaign/media-kit packaging from user input
- owner assets, media kits, proof review, reward eligibility, audit events
- Stripe checkout and signed webhook endpoint
- no private keys, no payout guarantees, no fabricated campaign metrics
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

import gradio as gr
import stripe
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, HttpUrl

APP_NAME = "MEMBRA Ads"
DB_PATH = Path(os.getenv("DB_PATH", "/tmp/membra_ads.sqlite3"))
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:7860").rstrip("/")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
stripe.api_key = STRIPE_SECRET_KEY or None
api = FastAPI(title=APP_NAME, version="0.2.0")


class CampaignIn(BaseModel):
    advertiser_email: str
    advertiser_name: str
    campaign_name: str
    destination_url: str
    budget_usd: float = Field(ge=0)
    surface_type: str
    geography: str
    proof_requirements: str = "photo, timestamp, location confirmation, visible QR/NFC marker"
    creative_notes: str = ""


class CheckoutIn(BaseModel):
    email: str
    campaign_id: str | None = None


class OwnerAssetIn(BaseModel):
    owner_id: str = "owner_demo"
    surface_type: str
    geography: str = "local"
    description: str
    consent_scope: str = "campaign-specific proof-media placement only"
    proof_requirements: str = "photo, timestamp, visible QR/NFC marker"


class MediaKitIn(BaseModel):
    campaign_id: str
    asset_id: str
    kit_type: str = "qr_sticker"
    creative_url: HttpUrl | None = None
    vendor: str = "manual"


class ProofIn(BaseModel):
    media_kit_id: str
    owner_id: str
    proof_url: HttpUrl | str
    location_hint: str = ""
    notes: str = ""


class ProofReviewIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|disputed|needs_more_evidence)$")
    reviewer: str = "operator"
    notes: str = ""


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def audit(conn: sqlite3.Connection, subject_type: str, subject_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    event_id = new_id("evt")
    body = {"event_id": event_id, "subject_type": subject_type, "subject_id": subject_id, "event_type": event_type, "payload": payload, "created_at": now()}
    proof_hash = canonical_hash(body)
    conn.execute(
        "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)",
        (event_id, subject_type, subject_id, event_type, json.dumps(payload, default=str), proof_hash, body["created_at"]),
    )
    return {**body, "proof_hash": proof_hash}


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS campaigns(
              campaign_id TEXT PRIMARY KEY,
              advertiser_email TEXT,
              advertiser_name TEXT,
              campaign_name TEXT,
              destination_url TEXT,
              budget_usd REAL,
              surface_type TEXT,
              geography TEXT,
              proof_requirements TEXT,
              creative_notes TEXT,
              status TEXT,
              stripe_session_id TEXT,
              created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS owner_assets(
              asset_id TEXT PRIMARY KEY,
              owner_id TEXT,
              surface_type TEXT,
              geography TEXT,
              description TEXT,
              consent_scope TEXT,
              proof_requirements TEXT,
              status TEXT,
              created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS media_kits(
              media_kit_id TEXT PRIMARY KEY,
              campaign_id TEXT,
              asset_id TEXT,
              qr_id TEXT,
              nfc_id TEXT,
              kit_type TEXT,
              creative_url TEXT,
              vendor TEXT,
              status TEXT,
              created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS proof_events(
              proof_id TEXT PRIMARY KEY,
              media_kit_id TEXT,
              campaign_id TEXT,
              asset_id TEXT,
              owner_id TEXT,
              proof_url TEXT,
              location_hint TEXT,
              notes TEXT,
              status TEXT,
              review_notes TEXT,
              reviewed_by TEXT,
              proof_hash TEXT,
              created_at TEXT,
              reviewed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reward_eligibility(
              reward_id TEXT PRIMARY KEY,
              campaign_id TEXT,
              asset_id TEXT,
              owner_id TEXT,
              proof_id TEXT,
              eligible_amount_usd REAL,
              status TEXT,
              reason TEXT,
              created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_events(
              event_id TEXT PRIMARY KEY,
              subject_type TEXT,
              subject_id TEXT,
              event_type TEXT,
              payload_json TEXT,
              proof_hash TEXT,
              created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS events(
              event_id TEXT PRIMARY KEY,
              campaign_id TEXT,
              event_type TEXT,
              payload_json TEXT,
              created_at TEXT
            );
            """
        )


init_db()


def build_campaign(data: CampaignIn) -> dict[str, Any]:
    campaign_id = new_id("cmp")
    qr_url = f"{APP_BASE_URL}/r/{campaign_id}"
    created_at = now()
    kit = {
        "campaign_id": campaign_id,
        "status": "draft_pending_funding_and_creative_approval",
        "advertiser": {"name": data.advertiser_name, "email": data.advertiser_email},
        "campaign": {"name": data.campaign_name, "destination_url": data.destination_url, "budget_usd": data.budget_usd, "geography": data.geography},
        "placement": {"surface_type": data.surface_type, "qr_redirect_url": qr_url, "nfc_id": "nfc_" + campaign_id[4:]},
        "proof_policy": {"requirements": data.proof_requirements, "payout_rule": "No approved proof means no payout eligibility."},
        "creative_notes": data.creative_notes,
        "created_at": created_at,
    }
    with db() as conn:
        conn.execute("INSERT INTO campaigns VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (campaign_id, data.advertiser_email, data.advertiser_name, data.campaign_name, data.destination_url, data.budget_usd, data.surface_type, data.geography, data.proof_requirements, data.creative_notes, kit["status"], None, created_at))
        audit(conn, "campaign", campaign_id, "campaign_created", kit)
    return kit


def campaign_table() -> list[dict[str, Any]]:
    return rows("SELECT campaign_id,campaign_name,advertiser_name,budget_usd,surface_type,geography,status,created_at FROM campaigns ORDER BY created_at DESC LIMIT 200")


def export_campaigns() -> str:
    table_rows = campaign_table()
    path = "/tmp/membra_ads_campaigns.csv"
    if table_rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
            writer.writeheader()
            writer.writerows(table_rows)
    else:
        Path(path).write_text("campaign_id,campaign_name,status\n", encoding="utf-8")
    return path


def ui_create(email, advertiser, name, destination, budget, surface, geography, proof, notes):
    try:
        data = CampaignIn(advertiser_email=email, advertiser_name=advertiser, campaign_name=name, destination_url=destination, budget_usd=float(budget or 0), surface_type=surface, geography=geography, proof_requirements=proof, creative_notes=notes)
        kit = build_campaign(data)
        return json.dumps(kit, indent=2), campaign_table(), export_campaigns()
    except Exception as exc:
        return f"Error: {exc}", campaign_table(), None


def ui_checkout(email, campaign_id):
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        return "Stripe is not configured."
    session = stripe.checkout.Session.create(mode="payment", customer_email=email, line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}], success_url=f"{APP_BASE_URL}/?checkout=success", cancel_url=f"{APP_BASE_URL}/?checkout=cancelled", metadata={"campaign_id": campaign_id or ""})
    if campaign_id:
        with db() as conn:
            conn.execute("UPDATE campaigns SET stripe_session_id=?, status=? WHERE campaign_id=?", (session.id, "funding_checkout_created", campaign_id))
            audit(conn, "campaign", campaign_id, "funding_checkout_created", {"stripe_session_id": session.id})
    return session.url


@api.get("/api/health")
def health():
    counts = {
        "campaigns": one("SELECT COUNT(*) c FROM campaigns")["c"],
        "assets": one("SELECT COUNT(*) c FROM owner_assets")["c"],
        "media_kits": one("SELECT COUNT(*) c FROM media_kits")["c"],
        "proof_events": one("SELECT COUNT(*) c FROM proof_events")["c"],
        "reward_events": one("SELECT COUNT(*) c FROM reward_eligibility")["c"],
    }
    return {"ok": True, "app": APP_NAME, "version": "0.2.0", "stripe_configured": bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET and STRIPE_PRICE_ID), "counts": counts}


@api.get("/api/campaigns")
def get_campaigns():
    return {"campaigns": campaign_table()}


@api.post("/api/campaigns")
def create_campaign(data: CampaignIn):
    return build_campaign(data)


@api.post("/api/assets")
def create_asset(data: OwnerAssetIn):
    asset_id = new_id("asset")
    created_at = now()
    row = {"asset_id": asset_id, **data.model_dump(), "status": "registered_pending_verification", "created_at": created_at}
    with db() as conn:
        conn.execute("INSERT INTO owner_assets VALUES(?,?,?,?,?,?,?,?,?)", (asset_id, data.owner_id, data.surface_type, data.geography, data.description, data.consent_scope, data.proof_requirements, row["status"], created_at))
        audit(conn, "asset", asset_id, "asset_registered", row)
    return row


@api.get("/api/assets")
def list_assets():
    return {"assets": rows("SELECT * FROM owner_assets ORDER BY created_at DESC")}


@api.post("/api/media-kits")
def create_media_kit(data: MediaKitIn):
    campaign = one("SELECT * FROM campaigns WHERE campaign_id=?", (data.campaign_id,))
    asset = one("SELECT * FROM owner_assets WHERE asset_id=?", (data.asset_id,))
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if not asset:
        raise HTTPException(404, "Asset not found")
    media_kit_id = new_id("kit")
    qr_id = "qr_" + media_kit_id[4:]
    nfc_id = "nfc_" + media_kit_id[4:]
    created_at = now()
    row = {
        "media_kit_id": media_kit_id,
        "campaign_id": data.campaign_id,
        "asset_id": data.asset_id,
        "qr_id": qr_id,
        "nfc_id": nfc_id,
        "kit_type": data.kit_type,
        "creative_url": str(data.creative_url or ""),
        "vendor": data.vendor,
        "status": "created_pending_receipt_and_proof",
        "created_at": created_at,
        "qr_redirect_url": f"{APP_BASE_URL}/r/{data.campaign_id}?kit={media_kit_id}",
    }
    with db() as conn:
        conn.execute("INSERT INTO media_kits VALUES(?,?,?,?,?,?,?,?,?,?)", (media_kit_id, data.campaign_id, data.asset_id, qr_id, nfc_id, data.kit_type, str(data.creative_url or ""), data.vendor, row["status"], created_at))
        audit(conn, "media_kit", media_kit_id, "media_kit_created", row)
    return row


@api.get("/api/media-kits")
def list_media_kits():
    return {"media_kits": rows("SELECT * FROM media_kits ORDER BY created_at DESC")}


@api.post("/api/proofs")
def submit_proof(data: ProofIn):
    kit = one("SELECT * FROM media_kits WHERE media_kit_id=?", (data.media_kit_id,))
    if not kit:
        raise HTTPException(404, "Media kit not found")
    proof_id = new_id("proof")
    created_at = now()
    payload = {"proof_id": proof_id, **data.model_dump(), "campaign_id": kit["campaign_id"], "asset_id": kit["asset_id"], "created_at": created_at}
    proof_hash = canonical_hash(payload)
    row = {**payload, "status": "submitted_pending_review", "proof_hash": proof_hash, "review_notes": "", "reviewed_by": "", "reviewed_at": ""}
    with db() as conn:
        conn.execute("INSERT INTO proof_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (proof_id, data.media_kit_id, kit["campaign_id"], kit["asset_id"], data.owner_id, str(data.proof_url), data.location_hint, data.notes, row["status"], "", "", proof_hash, created_at, ""))
        conn.execute("UPDATE media_kits SET status=? WHERE media_kit_id=?", ("proof_submitted_pending_review", data.media_kit_id))
        audit(conn, "proof", proof_id, "proof_submitted", row)
    return row


@api.get("/api/proofs")
def list_proofs():
    return {"proofs": rows("SELECT * FROM proof_events ORDER BY created_at DESC")}


@api.post("/api/proofs/{proof_id}/review")
def review_proof(proof_id: str, data: ProofReviewIn):
    proof = one("SELECT * FROM proof_events WHERE proof_id=?", (proof_id,))
    if not proof:
        raise HTTPException(404, "Proof not found")
    reviewed_at = now()
    with db() as conn:
        conn.execute("UPDATE proof_events SET status=?, review_notes=?, reviewed_by=?, reviewed_at=? WHERE proof_id=?", (data.decision, data.notes, data.reviewer, reviewed_at, proof_id))
        if data.decision == "approved":
            amount = max(float(one("SELECT budget_usd FROM campaigns WHERE campaign_id=?", (proof["campaign_id"],))["budget_usd"] or 0) * 0.1, 0)
            reward_id = new_id("reward")
            conn.execute("INSERT INTO reward_eligibility VALUES(?,?,?,?,?,?,?,?,?)", (reward_id, proof["campaign_id"], proof["asset_id"], proof["owner_id"], proof_id, round(amount, 2), "eligible_pending_external_settlement", "approved proof event", reviewed_at))
            conn.execute("UPDATE media_kits SET status=? WHERE media_kit_id=?", ("proof_approved_reward_eligible", proof["media_kit_id"]))
            audit(conn, "reward", reward_id, "reward_eligible", {"proof_id": proof_id, "eligible_amount_usd": round(amount, 2), "status": "eligible_pending_external_settlement"})
        else:
            conn.execute("UPDATE media_kits SET status=? WHERE media_kit_id=?", (f"proof_{data.decision}", proof["media_kit_id"]))
        audit(conn, "proof", proof_id, "proof_reviewed", {"decision": data.decision, "reviewer": data.reviewer, "notes": data.notes})
    return {"success": True, "proof_id": proof_id, "decision": data.decision}


@api.get("/api/reward-eligibility")
def list_rewards():
    return {"reward_eligibility": rows("SELECT * FROM reward_eligibility ORDER BY created_at DESC")}


@api.get("/api/audit-events")
def list_audit_events():
    return {"audit_events": rows("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 500")}


@api.post("/api/stripe/create-checkout-session")
def checkout(data: CheckoutIn):
    return {"url": ui_checkout(data.email, data.campaign_id or "")}


@api.post("/api/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None)):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(500, "STRIPE_WEBHOOK_SECRET is not configured")
    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    obj = event["data"]["object"]
    campaign_id = obj.get("metadata", {}).get("campaign_id")
    if campaign_id and event["type"] == "checkout.session.completed":
        with db() as conn:
            conn.execute("UPDATE campaigns SET status=? WHERE campaign_id=?", ("funded_pending_creative_approval", campaign_id))
            conn.execute("INSERT INTO events VALUES(?,?,?,?,?)", (new_id("evt"), campaign_id, event["type"], json.dumps(obj, default=str), now()))
            audit(conn, "campaign", campaign_id, "campaign_funded", {"stripe_event_id": event.get("id"), "type": event.get("type")})
    return JSONResponse({"received": True})


@api.get("/r/{campaign_id}")
def redirect_record(campaign_id: str):
    with db() as conn:
        row = conn.execute("SELECT destination_url FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
        conn.execute("INSERT INTO events VALUES(?,?,?,?,?)", (new_id("evt"), campaign_id, "scan", "{}", now()))
        audit(conn, "campaign", campaign_id, "qr_scan", {"campaign_id": campaign_id})
    if not row:
        raise HTTPException(404, "Campaign not found")
    return PlainTextResponse(f"MEMBRA scan recorded for {campaign_id}. Destination: {row['destination_url']}")


with gr.Blocks(title=APP_NAME) as demo:
    gr.Markdown("# MEMBRA Ads\nPhysical proof-media campaign control plane. No payout is released without approved proof.")
    with gr.Row():
        email = gr.Textbox(label="Advertiser email")
        advertiser = gr.Textbox(label="Advertiser name")
    name = gr.Textbox(label="Campaign name")
    destination = gr.Textbox(label="Destination URL")
    with gr.Row():
        budget = gr.Number(label="Budget USD", value=500)
        surface = gr.Dropdown(["car", "window", "shirt", "bag", "sticker", "NFC tag", "event badge"], label="Surface type", value="sticker")
        geography = gr.Textbox(label="Target geography", value="local")
    proof = gr.Textbox(label="Proof requirements", value="photo, timestamp, location confirmation, visible QR/NFC marker")
    notes = gr.Textbox(label="Creative notes", lines=3)
    create = gr.Button("Create campaign package", variant="primary")
    package = gr.Code(label="Campaign package", language="json")
    table = gr.Dataframe(label="Campaign register", value=campaign_table, interactive=False)
    export = gr.File(label="CSV export")
    with gr.Row():
        checkout_email = gr.Textbox(label="Checkout email")
        checkout_campaign = gr.Textbox(label="Campaign ID")
    checkout_btn = gr.Button("Create Stripe checkout")
    checkout_url = gr.Textbox(label="Checkout URL")
    create.click(ui_create, [email, advertiser, name, destination, budget, surface, geography, proof, notes], [package, table, export])
    checkout_btn.click(ui_checkout, [checkout_email, checkout_campaign], [checkout_url])

app = gr.mount_gradio_app(api, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
