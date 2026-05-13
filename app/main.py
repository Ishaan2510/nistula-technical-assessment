import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.models import InboundMessage, UnifiedMessage, WebhookResponse
from app.classifier import classify_query, count_match_strength
from app.claude_client import get_drafted_reply
from app.confidence import compute_confidence, get_action

load_dotenv()

app = FastAPI(
    title="Nistula Guest Message Handler",
    description="Webhook endpoint that normalises guest messages, classifies them, drafts AI replies via Claude, and returns a confidence-gated action.",
    version="1.0.0",
)


@app.post("/webhook/message", response_model=WebhookResponse)
async def handle_message(payload: InboundMessage):
    """
    Main webhook endpoint.

    Flow:
    1. Classify the inbound message into a query type.
    2. Normalise into the unified schema.
    3. Compute a confidence score based on classification strength and message clarity.
    4. Call Claude to draft a reply using property context and tone guide.
    5. Return the drafted reply, confidence score, and gated action.
    """
    try:
        query_type = classify_query(payload.message)
        match_strength = count_match_strength(payload.message, query_type)

        unified = UnifiedMessage(
            message_id=str(uuid.uuid4()),
            source=payload.source,
            guest_name=payload.guest_name,
            message_text=payload.message,
            timestamp=payload.timestamp,
            booking_ref=payload.booking_ref,
            property_id=payload.property_id,
            query_type=query_type,
        )

        confidence = compute_confidence(payload.message, query_type, match_strength)
        action = get_action(confidence, query_type)

        drafted_reply = get_drafted_reply(unified)

        return WebhookResponse(
            message_id=unified.message_id,
            query_type=query_type,
            drafted_reply=drafted_reply,
            confidence_score=confidence,
            action=action,
        )

    except ValueError as e:
        # Configuration errors (missing API key etc.)
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        # Claude API failures or unexpected errors
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unexpected server error: {str(exc)}"},
    )