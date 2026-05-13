# Nistula Technical Assessment

Guest message handler for the Nistula unified messaging platform. Built as part of the Summer Technology Internship 2026 assessment.

---

## What This Does

A FastAPI backend that:

1. Receives an inbound guest message from any channel (WhatsApp, Airbnb, Booking.com, Instagram, direct) via a POST webhook
2. Normalises it into a unified internal schema
3. Classifies the message into one of six query types
4. Calls the Claude API with property-specific context and query-type-specific tone instructions to draft a reply
5. Computes a confidence score and returns a gated action (auto_send, agent_review, or escalate)

---

## Project Structure

```
nistula-technical-assessment/
├── app/
│   ├── main.py           # FastAPI app and webhook endpoint
│   ├── models.py         # Pydantic request/response models
│   ├── classifier.py     # Rule-based query type classifier
│   ├── claude_client.py  # Claude API integration
│   └── confidence.py     # Confidence scoring and action gating
├── schema.sql            # Part 2: PostgreSQL schema
├── thinking.md           # Part 3: Written answers
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Ishaan2510/nistula-technical-assessment.git
cd nistula-technical-assessment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Open .env and add your ANTHROPIC_API_KEY
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

---

## Testing the Endpoint

The endpoint is `POST /webhook/message`.

### Test 1 — Availability enquiry (should auto_send)

```bash
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "source": "whatsapp",
    "guest_name": "Rahul Sharma",
    "message": "Is the villa available from April 20 to 24? What is the rate for 2 adults?",
    "timestamp": "2026-05-05T10:30:00Z",
    "booking_ref": "NIS-2024-0891",
    "property_id": "villa-b1"
  }'
```

Expected: `query_type: pre_sales_availability`, `action: auto_send`, confidence above 0.85.

---

### Test 2 — Complaint (should always escalate)

```bash
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "source": "airbnb",
    "guest_name": "Priya Mehta",
    "message": "There is no hot water and we have guests arriving for breakfast in 4 hours. This is unacceptable. I want a refund for tonight.",
    "timestamp": "2026-05-06T03:15:00Z",
    "booking_ref": "NIS-2024-0902",
    "property_id": "villa-b1"
  }'
```

Expected: `query_type: complaint`, `action: escalate`, confidence below 0.60.

---

### Test 3 — Post-booking check-in question (should auto_send or agent_review)

```bash
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "source": "direct",
    "guest_name": "Arjun Nair",
    "message": "What is the WiFi password? And can we check in at 1pm instead of 2?",
    "timestamp": "2026-05-07T11:00:00Z",
    "booking_ref": "NIS-2024-0915",
    "property_id": "villa-b1"
  }'
```

Expected: `query_type: post_sales_checkin`, reply includes WiFi password, `action: auto_send` or `agent_review` depending on mixed signals.

---

## Confidence Scoring Logic

The confidence score is a float between 0.0 and 1.0. It answers the question: how safe is it to auto-send this reply without a human reviewing it?

### Step 1 — Base score per query type

Each query type starts from a base confidence that reflects how well the static property context covers that category of question.

| Query type | Base confidence | Reasoning |
|---|---|---|
| pre_sales_availability | 0.92 | Availability and dates are fully in context |
| pre_sales_pricing | 0.90 | Rates are explicit in context |
| post_sales_checkin | 0.91 | WiFi, times, caretaker all in context |
| special_request | 0.68 | Often needs human confirmation |
| general_enquiry | 0.74 | Partially covered, may need human |
| complaint | 0.40 | Always escalates regardless |

### Step 2 — Classification signal strength

If 2 or more regex patterns fired during classification (strong signal), confidence gets a +0.05 boost. If 0 patterns fired (fell back to general_enquiry), confidence drops by 0.12. This reflects how certain the classifier is about the category.

### Step 3 — Message clarity penalty

Messages under 6 words are too vague for reliable AI replies. They incur a -0.10 penalty.

### Step 4 — Complaint hard cap

Complaints are always capped at 0.55 regardless of other signals. This forces the `escalate` action every time. Complaints are never auto-sent.

### Action thresholds

| Score | Action |
|---|---|
| 0.85 and above | auto_send |
| 0.60 to 0.84 | agent_review |
| Below 0.60 | escalate |
| Any complaint | escalate |

---

## Design Decisions

**Why rule-based classification instead of calling Claude to classify?**
Speed and cost. Every webhook call already makes one Claude API call to draft the reply. Adding a second call purely for classification doubles latency and doubles API cost per message. Keyword patterns are fast, cheap, and fully explainable. The tradeoff is they miss nuance — but for six well-defined categories with clear vocabulary, they perform well enough. In production I would add a feedback loop: when an agent overrides a classification, that correction trains an improved model.

**Why is the Claude prompt structured with a tone guide per query type?**
A reply to "is the villa available?" and a reply to "there is no hot water" should not sound the same. Generic "warm and helpful" prompting produces generic replies. Passing a specific tone instruction per query type (e.g. "acknowledge the problem first, do not be defensive") consistently shifts the reply quality without requiring a fine-tuned model.

**Why is property context static in the code rather than fetched from the database?**
For this assessment, the context is fixed. In production, property context would be fetched from the `properties` table using `property_id` from the webhook payload. The `claude_client.py` is structured with a `PROPERTY_CONTEXT` dict so the database fetch is a one-line substitution.

---

## Part 2 and Part 3

See `schema.sql` for the PostgreSQL schema with design decision comments.

See `thinking.md` for the written answers to the 3am scenario, system design, and pattern learning questions.