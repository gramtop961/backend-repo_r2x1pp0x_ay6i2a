"""
Database Schemas for ClassGuard AI

Each Pydantic model maps to a MongoDB collection whose name is the lowercase
of the class name, e.g. Student -> "student".

These schemas cover core entities needed for the MVP implementation across
attendance, exams, notes, courses, certificates/IDs, resumes and notifications.
"""
from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# User & Roles ---------------------------------------------------------------

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    role: Literal["student", "teacher", "parent", "admin"] = Field(...)
    is_active: bool = Field(True)

class Student(BaseModel):
    user_id: str = Field(..., description="Reference to user")
    category: Literal[
        "5-10",
        "11-12",
        "jee",
        "neet",
        "mht-cet",
        "engineering"
    ]
    roll_number: Optional[str] = None
    batch_id: Optional[str] = None
    parent_user_id: Optional[str] = Field(None, description="Linked parent user")
    locked_for_attendance: bool = Field(False, description="Auto-locked if <75% for engineering")

class Teacher(BaseModel):
    user_id: str
    subjects: List[str] = Field(default_factory=list)

class Parent(BaseModel):
    user_id: str
    children_user_ids: List[str] = Field(default_factory=list)

class Admin(BaseModel):
    user_id: str
    privileges: List[str] = Field(default_factory=list)

# Academic Structure ---------------------------------------------------------

class Subject(BaseModel):
    name: str
    category: Optional[str] = None

class Batch(BaseModel):
    name: str
    category: Optional[str] = None
    subject_ids: List[str] = Field(default_factory=list)

# Attendance -----------------------------------------------------------------

class AttendanceLog(BaseModel):
    student_id: str
    subject_id: Optional[str] = None
    batch_id: Optional[str] = None
    mode: Literal["face", "fingerprint", "rfid", "geo", "random_ai"]
    status: Literal["present", "absent"] = "present"
    device_id: Optional[str] = None
    proxy_detected: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Online Classes -------------------------------------------------------------

class OnlineClassSession(BaseModel):
    subject_id: str
    teacher_id: str
    scheduled_at: datetime
    auto_started: bool = False
    cancelled: bool = False

# Exams ----------------------------------------------------------------------

class Exam(BaseModel):
    title: str
    category: str
    subject_id: Optional[str] = None
    duration_minutes: int
    browser_lock: bool = True

class ExamViolation(BaseModel):
    exam_id: str
    student_id: str
    level: Literal[1, 2, 3]
    type: Literal["chat", "screen_switch", "camera_off", "mic_off", "other"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Notes / Documents ----------------------------------------------------------

class Note(BaseModel):
    title: str
    subject_id: Optional[str] = None
    teacher_id: str
    file_url: str
    file_type: Literal["pdf", "video", "image", "doc", "link"]
    folder: Optional[str] = None

# Courses & Assignments ------------------------------------------------------

class Course(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "engineering"
    modules: List[str] = Field(default_factory=list)

class Assignment(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

# Certificates & IDs ---------------------------------------------------------

class Certificate(BaseModel):
    student_id: str
    course_id: Optional[str] = None
    title: str
    qr_code: Optional[str] = None
    serial: Optional[str] = None
    issued_at: datetime = Field(default_factory=datetime.utcnow)

class IDCard(BaseModel):
    student_id: str
    roll_number: Optional[str] = None
    barcode: Optional[str] = None
    valid_till: Optional[datetime] = None

# Resume ---------------------------------------------------------------------

class Resume(BaseModel):
    student_id: str
    file_url: str
    approved: bool = False
    notes: Optional[str] = None

# Notifications ---------------------------------------------------------------

class Notification(BaseModel):
    user_id: str
    title: str
    message: str
    type: Literal[
        "warning",
        "notes",
        "exam",
        "certificate",
        "resume",
        "attendance",
        "study_suggestion"
    ] = "warning"
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Doubt Solver ---------------------------------------------------------------

class Doubt(BaseModel):
    user_id: str
    category: str
    question: str
    answer: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
