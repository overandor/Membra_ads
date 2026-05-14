"""MEMBRA Ads — physical proof media control plane for Hugging Face/FastAPI.

Production posture:
- deterministic campaign/media-kit packaging from user input
- Stripe checkout and signed webhook endpoint
- no private keys, no payout guarantees, no fabricated campaign metrics
"""
from __future__ import annotations

import csv
import datetime as dt
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
from pydantic import BaseModel, Field

APP_NAME = "MEMBRA Ads"
DB_PATH = Path(os.getenv("DB_PATH", "/tmp/membra_ads.sqlite3"))
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:7860").rstrip("/")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
stripe.api_key = STRIPE_SECRET_KEY or None
api = FastAPI(title=APP_NAME)

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


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript("""
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
        CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY, campaign_id TEXT, event_type TEXT, payload_json TEXT, created_at TEXT);
        """)

init_db()


def build_campaign(data: CampaignIn) -> dict[str, Any]:
    campaign_id = "cmp_" + uuid.uuid4().hex[:12]
    qr_url = f"{APP_BASE_URL}/r/{campaign_id}"
    kit = {
        "campaign_id": campaign_id,
        "status": "draft_pending_funding_and_creative_approval",
        "advertiser": {"name": data.advertiser_name, "email": data.advertiser_email},
        "campaign": {"name": data.campaign_name, "destination_url": data.destination_url, "budget_usd": data.budget_usd, "geography": data.geography},
        "placement": {"surface_type": data.surface_type, "qr_redirect_url": qr_url, "nfc_id": "nfc_" + campaign_id[4:]},
        "proof_policy": {"requirements": data.proof_requirements, "payout_rule": "No approved proof means no payout eligibility."},
        "creative_notes": data.creative_notes,
        "created_at": now(),
    }
    with db() as conn:
        conn.execute("INSERT INTO campaigns VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (campaign_id, data.advertiser_email, data.advertiser_name, data.campaign_name, data.destination_url, data.budget_usd, data.surface_type, data.geography, data.proof_requirements, data.creative_notes, kit["status"], None, kit["created_at"]))
    return kit


def campaign_table() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT campaign_id,campaign_name,advertiser_name,budget_usd,surface_type,geography,status,created_at FROM campaigns ORDER BY created_at DESC LIMIT 200").fetchall()
    return [dict(r) for r in rows]


def export_campaigns() -> str:
    rows = campaign_table()
    path = "/tmp/membra_ads_campaigns.csv"
    if rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader(); writer.writerows(rows)
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
    return session.url

@api.get("/api/health")
def health():
    return {"ok": True, "app": APP_NAME, "stripe_configured": bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET and STRIPE_PRICE_ID)}

@api.get("/api/campaigns")
def get_campaigns():
    return {"campaigns": campaign_table()}

@api.post("/api/campaigns")
def create_campaign(data: CampaignIn):
    return build_campaign(data)

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
            conn.execute("INSERT INTO events VALUES(?,?,?,?,?)", ("evt_" + uuid.uuid4().hex[:12], campaign_id, event["type"], json.dumps(obj, default=str), now()))
    return JSONResponse({"received": True})

@api.get("/r/{campaign_id}")
def redirect_record(campaign_id: str):
    with db() as conn:
        row = conn.execute("SELECT destination_url FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
        conn.execute("INSERT INTO events VALUES(?,?,?,?,?)", ("evt_" + uuid.uuid4().hex[:12], campaign_id, "scan", "{}", now()))
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
