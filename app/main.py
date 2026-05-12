import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.models import InboundMessage, UnifiedMessage, WebhookResponse
from app.classifier import classify_query, count_match_strength
from app.claude_client import get_drafted_reply
from app.confidence import compute_confidence, get_action

load_dotenv()

app = FastAPI(title="Nistula Guest Message Handler")

@app.get("/health")
async def health():
    return {"status": "ok"}