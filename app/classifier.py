import re
from app.models import QueryType


# Ordered dict — complaint checked first because it overrides everything else.
# Each key maps to a list of regex patterns. More patterns = stronger signal.
CLASSIFICATION_RULES: dict[QueryType, list[str]] = {
    QueryType.complaint: [
        r"\bnot (working|happy|ok|okay|good|satisfied|acceptable)\b",
        r"\b(broken|issue|problem|fault|damage|dirty|unclean)\b",
        r"\b(unacceptable|disappointed|terrible|worst|awful|horrible)\b",
        r"\brefund\b",
        r"\bno (hot water|ac|wifi|power|electricity|internet)\b",
        r"\b(doesn't|won't|isn't|aren't|can't|cannot) work\b",
        r"\bstill (not|no)\b",
        r"\bwant (my )?money back\b",
    ],
    QueryType.pre_sales_availability: [
        r"\bavailab\w+\b",
        r"\bany (rooms?|villas?|slots?)\b",
        r"\bfrom\s+\w+\s+to\b",
        r"\b(check.?in|arrive|arrival).*(check.?out|depart|departure)\b",
        r"\b(april|may|june|july|august|september|october|november|december|january|february|march)\b.*\b(night|days?|week)\b",
        r"\b\d{1,2}\s*(to|-)\s*\d{1,2}\b",
        r"\bbook\b.*\b(night|week|days?)\b",
    ],
    QueryType.pre_sales_pricing: [
        r"\b(rate|rates|tariff|pricing|price|prices|cost|costs)\b",
        r"\bhow much\b",
        r"\bper night\b",
        r"\bfor \d+ (adults?|guests?|people|persons?|pax)\b",
        r"\bcharge\b",
        r"\bquote\b",
        r"\bpackage\b",
    ],
    QueryType.post_sales_checkin: [
        r"\bcheck.?in (time|process|procedure)\b",
        r"\bcheck.?out (time|process|procedure)\b",
        r"\bwifi\b",
        r"\bpassword\b",
        r"\b(how to|how do i|how do we) (get|reach|find|arrive|come)\b",
        r"\bdirections?\b",
        r"\bwhen can (i|we) (check|arrive|come|enter|access)\b",
        r"\bkey\b.*\b(handover|collection|pickup)\b",
    ],
    QueryType.special_request: [
        r"\bearl(y|ier) check.?in\b",
        r"\blate check.?out\b",
        r"\b(airport|cab|car|taxi).*(transfer|pickup|drop|transport)\b",
        r"\b(birthday|anniversary|honeymoon|celebration|surprise)\b",
        r"\bdecor\w*\b",
        r"\bchef\b",
        r"\bcook\b",
        r"\bspecial (arrangement|setup|request)\b",
        r"\bflowers?\b",
        r"\bcake\b",
    ],
}


def classify_query(message: str) -> QueryType:
    """
    Rule-based classifier. Complaint checked first — it always escalates
    regardless of other signals. Other categories scored by pattern match
    count; highest score wins. Falls back to general_enquiry.
    """
    text = message.lower()

    # Complaint is priority — one match is enough to classify
    for pattern in CLASSIFICATION_RULES[QueryType.complaint]:
        if re.search(pattern, text):
            return QueryType.complaint

    scores: dict[QueryType, int] = {}
    for query_type, patterns in CLASSIFICATION_RULES.items():
        if query_type == QueryType.complaint:
            continue
        scores[query_type] = sum(1 for p in patterns if re.search(p, text))

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best

    return QueryType.general_enquiry


def count_match_strength(message: str, query_type: QueryType) -> int:
    """Returns how many patterns fired for the winning query type."""
    text = message.lower()
    patterns = CLASSIFICATION_RULES.get(query_type, [])
    return sum(1 for p in patterns if re.search(p, text))