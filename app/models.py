from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SourceChannel(str, Enum):
    whatsapp = "whatsapp"
    booking_com = "booking_com"
    airbnb = "airbnb"
    instagram = "instagram"
    direct = "direct"


class QueryType(str, Enum):
    pre_sales_availability = "pre_sales_availability"
    pre_sales_pricing = "pre_sales_pricing"
    post_sales_checkin = "post_sales_checkin"
    special_request = "special_request"
    complaint = "complaint"
    general_enquiry = "general_enquiry"


class InboundMessage(BaseModel):
    source: SourceChannel
    guest_name: str
    message: str
    timestamp: str
    booking_ref: Optional[str] = None
    property_id: str


class UnifiedMessage(BaseModel):
    message_id: str
    source: SourceChannel
    guest_name: str
    message_text: str
    timestamp: str
    booking_ref: Optional[str] = None
    property_id: str
    query_type: QueryType


class WebhookResponse(BaseModel):
    message_id: str
    query_type: QueryType
    drafted_reply: str
    confidence_score: float
    action: str