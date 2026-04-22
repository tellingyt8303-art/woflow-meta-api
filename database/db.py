import firebase_admin
from firebase_admin import credentials, firestore, auth
from config import FIREBASE_CREDENTIALS_PATH, FIREBASE_DATABASE_URL

_db = None

def init_firebase():
    """Initialize Firebase app (called once at startup)."""
    global _db
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            "databaseURL": FIREBASE_DATABASE_URL
        })
    _db = firestore.client()
    return _db

def get_db() -> firestore.Client:
    """Return Firestore client, initializing if needed."""
    global _db
    if _db is None:
        init_firebase()
    return _db

# ─── Generic CRUD Helpers ────────────────────────────────────

def create_doc(collection: str, data: dict, doc_id: str = None) -> str:
    """Create a document. Returns the document ID."""
    db = get_db()
    if doc_id:
        db.collection(collection).document(doc_id).set(data)
        return doc_id
    else:
        ref = db.collection(collection).add(data)
        return ref[1].id

def get_doc(collection: str, doc_id: str) -> dict | None:
    """Get a single document by ID."""
    db = get_db()
    doc = db.collection(collection).document(doc_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None

def update_doc(collection: str, doc_id: str, data: dict):
    """Update fields in a document."""
    db = get_db()
    db.collection(collection).document(doc_id).update(data)

def delete_doc(collection: str, doc_id: str):
    """Delete a document."""
    db = get_db()
    db.collection(collection).document(doc_id).delete()

def query_docs(collection: str, filters: list = None, limit: int = 100) -> list:
    """
    Query documents with optional filters.
    filters: list of tuples (field, operator, value)
    e.g. [("client_id", "==", "abc123"), ("status", "==", "open")]
    """
    db = get_db()
    ref = db.collection(collection)
    if filters:
        for field, op, value in filters:
            ref = ref.where(field, op, value)
    docs = ref.limit(limit).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]

def get_all_docs(collection: str) -> list:
    """Get all documents in a collection."""
    db = get_db()
    docs = db.collection(collection).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]
