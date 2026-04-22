import os
from dotenv import load_dotenv

load_dotenv()

# ─── Meta Cloud API ──────────────────────────────────────────
# Aapka ek Meta App — sabke liye shared
META_APP_ID           = os.getenv("META_APP_ID", "")
META_APP_SECRET       = os.getenv("META_APP_SECRET", "")
META_VERIFY_TOKEN     = os.getenv("META_VERIFY_TOKEN", "waflow_webhook_secret")
META_API_VERSION      = "v19.0"
META_API_BASE         = f"https://graph.facebook.com/{META_API_VERSION}"

# ─── Firebase ────────────────────────────────────────────────
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
FIREBASE_DATABASE_URL     = os.getenv("FIREBASE_DATABASE_URL", "")

# ─── App ─────────────────────────────────────────────────────
SECRET_KEY                  = os.getenv("SECRET_KEY", "change-this-secret")
ALGORITHM                   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# ─── Follow-up Config ────────────────────────────────────────
DEFAULT_FOLLOWUP_INTERVALS = [1, 3, 7]  # days

# ─── Firestore Collections ───────────────────────────────────
COLLECTION_CLIENTS   = "clients"
COLLECTION_LEADS     = "leads"
COLLECTION_MESSAGES  = "messages"
COLLECTION_FOLLOWUPS = "followups"
COLLECTION_TEMPLATES = "templates"
COLLECTION_USERS     = "users"
