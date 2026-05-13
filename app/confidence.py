from app.models import QueryType


# Base confidence per query type reflects how well the static property
# context covers that category of question.
# Availability and pricing details are fully in context -> high base.
# Special requests often need human confirmation -> lower base.
# Complaints always escalate -> hard-capped below 0.60.
BASE_CONFIDENCE: dict[QueryType, float] = {
    QueryType.pre_sales_availability: 0.92,
    QueryType.pre_sales_pricing: 0.90,
    QueryType.post_sales_checkin: 0.91,
    QueryType.special_request: 0.68,
    QueryType.general_enquiry: 0.74,
    QueryType.complaint: 0.40,
}


def compute_confidence(
    message: str,
    query_type: QueryType,
    match_strength: int,
) -> float:
    """
    Confidence score logic:

    1. Start from a base score per query type (how well context covers it).
    2. Add a small boost if the classifier fired multiple strong signals
       (less ambiguous classification = higher reply reliability).
    3. Penalise very short or vague messages — fewer words means less
       context for the AI to work with.
    4. Hard-cap complaints below 0.60 to force escalation regardless of
       how well the reply was drafted.

    Final score is clamped to [0.0, 1.0] and rounded to 2 decimal places.
    """
    score = BASE_CONFIDENCE[query_type]

    # Multi-signal boost: if 2+ patterns fired, classification is reliable
    if match_strength >= 2:
        score = min(score + 0.05, 1.0)
    elif match_strength == 0:
        # Zero pattern matches means we fell back to general_enquiry
        score -= 0.12

    # Penalise very short messages — under 6 words is usually too vague
    word_count = len(message.split())
    if word_count < 6:
        score -= 0.10

    # Complaints always force escalation path
    if query_type == QueryType.complaint:
        return round(min(score, 0.55), 2)

    return round(max(0.0, min(1.0, score)), 2)


def get_action(confidence: float, query_type: QueryType) -> str:
    """
    Maps confidence score to action.
    Complaint always escalates — never auto-sent regardless of score.
    """
    if query_type == QueryType.complaint:
        return "escalate"
    if confidence >= 0.85:
        return "auto_send"
    if confidence >= 0.60:
        return "agent_review"
    return "escalate"