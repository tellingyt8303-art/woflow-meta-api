from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ─── Enums ───────────────────────────────────────────────────

class LeadStatus(str, Enum):
    new       = "new"
    contacted = "contacted"
    qualified = "qualified"
    converted = "converted"
    lost      = "lost"

class FollowupStatus(str, Enum):
    pending   = "pending"
    sent      = "sent"
    failed    = "failed"
    cancelled = "cancelled"

class MessageDirection(str, Enum):
    inbound  = "inbound"
    outbound = "outbound"

# ─── Client ──────────────────────────────────────────────────

class Client(BaseModel):
    id: Optional[str]                  = None
    name: str
    email: str
    business_name: str
    industry: Optional[str]            = None
    active: bool                        = True
    # Meta Cloud API fields
    meta_phone_number_id: Optional[str] = None   # Meta ka Phone Number ID
    meta_access_token: Optional[str]    = None   # Permanent Access Token
    whatsapp_number: Optional[str]      = None   # e.g. "+919876543210"
    wa_verified_name: Optional[str]     = None   # Meta verified business name
    wa_connected: bool                  = False
    wa_connected_at: Optional[str]      = None
    created_at: str                     = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ─── Lead ────────────────────────────────────────────────────

class Lead(BaseModel):
    id: Optional[str]         = None
    client_id: str
    phone: str                 # e.g. "919876543210" (Meta format, no +)
    name: Optional[str]       = None
    email: Optional[str]      = None
    status: LeadStatus         = LeadStatus.new
    source: str                = "whatsapp"
    notes: Optional[str]      = None
    tags: List[str]            = []
    created_at: str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str            = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ─── Message Log ─────────────────────────────────────────────

class MessageLog(BaseModel):
    id: Optional[str]              = None
    client_id: str
    lead_phone: str
    direction: MessageDirection
    body: str
    template_id: Optional[str]     = None
    meta_message_id: Optional[str] = None   # Meta ka message ID (wamid)
    timestamp: str                  = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ─── Template ────────────────────────────────────────────────

class Template(BaseModel):
    id: Optional[str]           = None
    client_id: str
    name: str
    trigger_keywords: List[str]  = []
    message_body: str            # {name}, {business} placeholders support
    is_default: bool             = False
    active: bool                 = True
    created_at: str              = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ─── Follow-up ───────────────────────────────────────────────

class Followup(BaseModel):
    id: Optional[str]          = None
    client_id: str
    lead_phone: str
    template_id: Optional[str] = None
    message_body: str
    scheduled_at: str
    status: FollowupStatus      = FollowupStatus.pending
    attempt: int                = 1
    created_at: str             = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ─── Auth ────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    business_name: str

class UserLogin(BaseModel):
    email: str
    password: str

# ─── WhatsApp Connect Request ────────────────────────────────

class WhatsAppConnectRequest(BaseModel):
    phone_number_id: str   # Meta Dashboard se copy karo
    access_token: str      # Meta Permanent Token
