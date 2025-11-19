import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import (
    User, Student, Teacher, Parent, Admin,
    Subject, Batch,
    AttendanceLog,
    OnlineClassSession,
    Exam, ExamViolation,
    Note,
    Course, Assignment,
    Certificate, IDCard,
    Resume,
    Notification,
    Doubt,
)

app = FastAPI(title="ClassGuard AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------- Utilities ----------------------------

def _collection(name: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    return db[name]


def _as_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# ---------------------------- Health -------------------------------

@app.get("/")
def root():
    return {"message": "ClassGuard AI backend is running"}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/test")
def test_database():
    resp = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            resp["database"] = "✅ Available"
            resp["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            resp["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                cols = db.list_collection_names()
                resp["collections"] = cols
                resp["connection_status"] = "Connected"
                resp["database"] = "✅ Connected & Working"
            except Exception as e:
                resp["database"] = f"⚠️ Connected but error: {str(e)[:80]}"
        else:
            resp["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        resp["database"] = f"❌ Error: {str(e)[:80]}"
    return resp


# ---------------------------- Users & Roles ------------------------

@app.post("/api/users")
def create_user(payload: User):
    _id = create_document("user", payload)
    return {"id": _id}


@app.post("/api/students")
def create_student(payload: Student):
    _id = create_document("student", payload)
    return {"id": _id}


@app.get("/api/students/{student_id}")
def get_student(student_id: str):
    doc = _collection("student").find_one({"_id": __import__("bson").ObjectId(student_id)})
    if not doc:
        raise HTTPException(404, "Student not found")
    return _as_str_id(doc)


# ---------------------------- Attendance --------------------------

@app.post("/api/attendance")
def log_attendance(payload: AttendanceLog):
    _id = create_document("attendancelog", payload)
    return {"id": _id}


class AttendanceSummary(BaseModel):
    total: int
    present: int
    absent: int
    percentage: float
    locked_for_attendance: bool


@app.get("/api/students/{student_id}/attendance/summary", response_model=AttendanceSummary)
def attendance_summary(student_id: str, days: int = Query(120, ge=1, le=365)):
    # Fetch student
    student = _collection("student").find_one({"_id": __import__("bson").ObjectId(student_id)})
    if not student:
        raise HTTPException(404, "Student not found")

    since = datetime.utcnow() - timedelta(days=days)
    logs = list(_collection("attendancelog").find({
        "student_id": student_id,
        "timestamp": {"$gte": since}
    }))
    total = len(logs)
    present = sum(1 for l in logs if l.get("status", "present") == "present")
    absent = total - present
    percentage = round((present / total) * 100, 2) if total else 0.0

    locked = bool(student.get("locked_for_attendance", False))
    # Auto-lock rule for engineering
    if student.get("category") == "engineering":
        should_lock = percentage < 75.0
        if should_lock != locked:
            _collection("student").update_one(
                {"_id": student["_id"]}, {"$set": {"locked_for_attendance": should_lock}}
            )
            locked = should_lock

    return AttendanceSummary(
        total=total, present=present, absent=absent, percentage=percentage,
        locked_for_attendance=locked,
    )


@app.post("/api/students/{student_id}/lock")
def manual_lock(student_id: str):
    res = _collection("student").update_one({"_id": __import__("bson").ObjectId(student_id)}, {"$set": {"locked_for_attendance": True}})
    if res.matched_count == 0:
        raise HTTPException(404, "Student not found")
    return {"locked": True}


@app.post("/api/students/{student_id}/unlock")
def manual_unlock(student_id: str):
    res = _collection("student").update_one({"_id": __import__("bson").ObjectId(student_id)}, {"$set": {"locked_for_attendance": False}})
    if res.matched_count == 0:
        raise HTTPException(404, "Student not found")
    return {"locked": False}


# ---------------------------- Notes --------------------------------

@app.post("/api/notes")
def create_note(payload: Note):
    _id = create_document("note", payload)
    return {"id": _id}


@app.get("/api/notes")
def list_notes(subject_id: Optional[str] = None, teacher_id: Optional[str] = None):
    qry: Dict[str, Any] = {}
    if subject_id:
        qry["subject_id"] = subject_id
    if teacher_id:
        qry["teacher_id"] = teacher_id
    docs = list(_collection("note").find(qry).sort("_id", -1).limit(100))
    return [_as_str_id(d) for d in docs]


# ---------------------------- Certificates & IDs -------------------

@app.post("/api/certificates")
def create_certificate(payload: Certificate):
    _id = create_document("certificate", payload)
    return {"id": _id}


@app.get("/api/certificates/{cert_id}")
def get_certificate(cert_id: str):
    doc = _collection("certificate").find_one({"_id": __import__("bson").ObjectId(cert_id)})
    if not doc:
        raise HTTPException(404, "Certificate not found")
    return _as_str_id(doc)


@app.post("/api/idcards")
def create_idcard(payload: IDCard):
    _id = create_document("idcard", payload)
    return {"id": _id}


@app.get("/api/idcards/{card_id}")
def get_idcard(card_id: str):
    doc = _collection("idcard").find_one({"_id": __import__("bson").ObjectId(card_id)})
    if not doc:
        raise HTTPException(404, "ID Card not found")
    return _as_str_id(doc)


# ---------------------------- Resumes ------------------------------

@app.post("/api/resumes")
def upload_resume(payload: Resume):
    _id = create_document("resume", payload)
    return {"id": _id}


@app.get("/api/resumes/{student_id}")
def get_resume(student_id: str):
    doc = _collection("resume").find_one({"student_id": student_id})
    if not doc:
        raise HTTPException(404, "Resume not found")
    return _as_str_id(doc)


# ---------------------------- Notifications -----------------------

@app.post("/api/notifications")
def create_notification(payload: Notification):
    _id = create_document("notification", payload)
    return {"id": _id}


@app.get("/api/notifications")
def list_notifications(user_id: str):
    docs = list(_collection("notification").find({"user_id": user_id}).sort("created_at", -1).limit(100))
    return [_as_str_id(d) for d in docs]


# ---------------------------- Doubt Solver (placeholder) ----------

@app.post("/api/doubts")
def create_doubt(payload: Doubt):
    # Placeholder answer for MVP
    if not payload.answer:
        payload.answer = "This is a placeholder explanation. In production, this will be answered by the AI solver with steps, formulas, and diagrams."
    _id = create_document("doubt", payload)
    return {"id": _id, "answer": payload.answer}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
