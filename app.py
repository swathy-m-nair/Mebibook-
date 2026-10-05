# MediBook - Doctor Appointment System
# Built with Flask + SQLite

from datetime import UTC, date, datetime
from pathlib import Path
import shutil
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
PRIMARY_DB_PATH = INSTANCE_DIR / "medibook.db"
LEGACY_DB_PATH = BASE_DIR / "medibook.db"

INSTANCE_DIR.mkdir(exist_ok=True)
if not PRIMARY_DB_PATH.exists() and LEGACY_DB_PATH.exists():
    shutil.copy2(LEGACY_DB_PATH, PRIMARY_DB_PATH)

app = Flask(__name__)
app.secret_key = "medibook_secret_2024"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{PRIMARY_DB_PATH.as_posix()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Valid tab names for each role's dashboard
ADMIN_TABS    = {"appointments", "doctors", "patients"}
DOCTOR_TABS   = {"appointments", "availability", "messages"}
PATIENT_TABS  = {"appointments", "messages"}
HOSPITAL_TABS = {"appointments", "doctors"}

DEFAULT_DOCTOR_PASSWORD   = "doctor123"
DEFAULT_HOSPITAL_PASSWORD = "hospital123"

# Use pbkdf2:sha256 everywhere — works on all platforms and all werkzeug versions
HASH_METHOD = "pbkdf2:sha256"

ALL_TIME_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
    "12:00 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "05:00 PM",
]

# Auto-generated bios by specialty
SPECIALTY_BIOS = {
    "Cardiology":       "Senior cardiologist focused on preventive heart care, cardiac diagnostics, and long-term recovery planning for patients across {city}.",
    "Neurology":        "Neurologist experienced in stroke care, migraine management, epilepsy evaluation, and complex neurological follow-up at {hospital}.",
    "Pediatrics":       "Pediatrician known for newborn care, vaccination planning, and family-centered treatment for infants, children, and teenagers.",
    "Dermatology":      "Dermatologist treating acne, eczema, psoriasis, hair loss, and skin infections with a strong focus on practical long-term care.",
    "Orthopedics":      "Orthopedic specialist handling fractures, joint pain, sports injuries, and rehabilitation plans for active patients and seniors alike.",
    "General Medicine": "General physician providing first-contact care, preventive screenings, diabetes and BP follow-up, and same-day illness management.",
    "Gynecology":       "Gynecologist supporting reproductive health, menstrual concerns, antenatal checkups, and preventive care for women of all ages.",
    "Ophthalmology":    "Ophthalmologist managing cataract care, glaucoma screening, diabetic eye follow-up, and routine vision consultations.",
    "ENT":              "ENT specialist treating sinus issues, throat infections, allergies, hearing concerns, and day-to-day ear, nose, and throat problems.",
    "Gastroenterology": "Gastroenterologist focused on acidity, liver disorders, IBS, endoscopy follow-up, and digestive health restoration.",
    "Pulmonology":      "Pulmonologist managing asthma, COPD, sleep-related breathing issues, allergies, and recovery care after lung infections.",
    "Nephrology":       "Nephrologist experienced in kidney disease monitoring, dialysis planning, fluid balance care, and hypertension-related kidney issues.",
    "Oncology":         "Oncology specialist supporting early diagnosis, chemotherapy planning, follow-up care, and patient-centered cancer counseling.",
    "Endocrinology":    "Endocrinologist focused on diabetes, thyroid disorders, hormonal imbalance, obesity care, and metabolic health management.",
    "Urology":          "Urologist treating kidney stones, urinary infections, prostate conditions, and minimally invasive procedural follow-up.",
    "Psychiatry":       "Psychiatrist providing structured care for stress, anxiety, depression, sleep disorders, and long-term emotional wellbeing.",
}

# Seed doctors for Tamil Nadu hospitals
BASE_DOCTOR_SEEDS = [
    {"name": "Dr. Ravi Kumar",     "specialty": "Cardiology",       "fee": 800,  "hospital": "Apollo Hospitals, Chennai",              "city": "Chennai",     "experience": 18, "bio": "Senior cardiologist with 18 years of experience in interventional cardiology and heart failure management. Trained at AIIMS Delhi."},
    {"name": "Dr. Priya Nair",     "specialty": "Neurology",        "fee": 900,  "hospital": "MIOT International, Chennai",            "city": "Chennai",     "experience": 14, "bio": "Expert in stroke, epilepsy, and movement disorders. Fellowship from Mayo Clinic, USA. Published 30+ research papers in neurology."},
    {"name": "Dr. Arun Menon",     "specialty": "Pediatrics",       "fee": 600,  "hospital": "Rainbow Children's Hospital, Chennai",   "city": "Chennai",     "experience": 10, "bio": "Dedicated pediatrician specializing in neonatal care and childhood immunization. Known for compassionate care for young patients and anxious parents."},
    {"name": "Dr. Sneha Thomas",   "specialty": "Dermatology",      "fee": 700,  "hospital": "Skin & Smile Clinic, T. Nagar",         "city": "Chennai",     "experience":  9, "bio": "Cosmetic and clinical dermatologist with expertise in acne, psoriasis, and laser treatments. Trained at NIMHANS Bangalore."},
    {"name": "Dr. Sanjay Pillai",  "specialty": "Orthopedics",      "fee": 850,  "hospital": "Fortis Malar Hospital, Adyar",          "city": "Chennai",     "experience": 20, "bio": "Leading orthopedic surgeon specializing in joint replacement and sports injuries. Over 2000 successful surgeries; faculty at Madras Medical College."},
    {"name": "Dr. Anita Varma",    "specialty": "General Medicine",  "fee": 500,  "hospital": "MediBook Primary Care, Anna Nagar",     "city": "Chennai",     "experience": 12, "bio": "Trusted general physician offering holistic primary care, chronic disease management, and preventive health screenings for all age groups."},
    {"name": "Dr. Vikram Nambiar", "specialty": "Cardiology",       "fee": 950,  "hospital": "Kauvery Hospital, Trichy",              "city": "Trichy",      "experience": 22, "bio": "Pioneer in minimally invasive cardiac procedures with 22 years of practice across Chennai and Trichy. Fellowship from Royal College of Surgeons, UK."},
    {"name": "Dr. Lakshmi Iyer",   "specialty": "Gynecology",       "fee": 750,  "hospital": "GEM Hospital, Coimbatore",              "city": "Coimbatore",  "experience": 16, "bio": "Senior gynecologist and laparoscopic surgeon. Expert in high-risk pregnancies, PCOS management, and reproductive health for women of all ages."},
    {"name": "Dr. Suresh Babu",    "specialty": "Ophthalmology",    "fee": 650,  "hospital": "Aravind Eye Hospital, Madurai",         "city": "Madurai",     "experience": 13, "bio": "Experienced ophthalmologist specializing in cataract surgery, glaucoma treatment, and retinal disorders. Part of Aravind's pioneering vision care team."},
    {"name": "Dr. Kavitha Raj",    "specialty": "ENT",              "fee": 550,  "hospital": "Sri Ramachandra Medical Centre, Porur", "city": "Chennai",     "experience":  8, "bio": "ENT surgeon specializing in sinus disorders, hearing loss, and pediatric ENT. Known for minimally invasive endoscopic procedures."},
]

# Seed doctors for Kerala hospitals
KERALA_DOCTOR_GROUPS = [
    {"hospital": "Aster Medcity, Kochi",                         "city": "Kochi",              "doctors": [("Dr. Anoop Menon", "Cardiology", 950, 18), ("Dr. Meera Kurup", "Neurology", 900, 14), ("Dr. Vivek Nair", "Gastroenterology", 850, 12), ("Dr. Liji Thomas", "Endocrinology", 800, 11)]},
    {"hospital": "Amrita Hospital, Kochi",                       "city": "Kochi",              "doctors": [("Dr. Sandeep Varghese", "Oncology", 1100, 20), ("Dr. Asha Balan", "Pediatrics", 650, 10), ("Dr. Rahul Krishnan", "Orthopedics", 900, 16), ("Dr. Deepa Mathew", "Nephrology", 920, 15)]},
    {"hospital": "Rajagiri Hospital, Aluva",                     "city": "Aluva",              "doctors": [("Dr. Nikhil Joseph", "Pulmonology", 780, 11), ("Dr. Renu Nambiar", "ENT", 620, 9), ("Dr. Arjun Paul", "Urology", 870, 14), ("Dr. Neethu R. Pillai", "Gynecology", 760, 13)]},
    {"hospital": "VPS Lakeshore Hospital, Kochi",                "city": "Kochi",              "doctors": [("Dr. Harishankar Menon", "Cardiology", 980, 19), ("Dr. Anjana George", "Dermatology", 720, 8), ("Dr. Biju Mathew", "General Medicine", 560, 17), ("Dr. Reshma Kurian", "Psychiatry", 750, 12)]},
    {"hospital": "KIMSHEALTH, Thiruvananthapuram",               "city": "Thiruvananthapuram", "doctors": [("Dr. Adithya Kumar", "Neurology", 930, 15), ("Dr. Sreelakshmi Nair", "Ophthalmology", 690, 10), ("Dr. Tony Chacko", "Oncology", 1080, 18), ("Dr. Devika Mohan", "Endocrinology", 820, 11)]},
    {"hospital": "Ananthapuri Hospitals, Thiruvananthapuram",    "city": "Thiruvananthapuram", "doctors": [("Dr. Gokul Das", "General Medicine", 540, 9), ("Dr. Priyanka Pillai", "Gynecology", 780, 14), ("Dr. Ajith Babu", "Orthopedics", 880, 17), ("Dr. Sneha R. Menon", "Dermatology", 710, 9)]},
    {"hospital": "SP Fort Hospital, Thiruvananthapuram",         "city": "Thiruvananthapuram", "doctors": [("Dr. Renjith Nair", "Cardiology", 910, 16), ("Dr. Malavika S.", "Urology", 850, 12), ("Dr. Nandita Kuruvilla", "Pediatrics", 640, 11), ("Dr. Harikrishnan S.", "ENT", 600, 8)]},
    {"hospital": "Aster MIMS Hospital, Kozhikode",               "city": "Kozhikode",          "doctors": [("Dr. Abdul Rahman K.", "Gastroenterology", 860, 13), ("Dr. Faseela Moidu", "Pulmonology", 790, 10), ("Dr. Jithin Mathew", "Nephrology", 940, 15), ("Dr. Keerthana R.", "Psychiatry", 730, 9)]},
    {"hospital": "Baby Memorial Hospital, Kozhikode",            "city": "Kozhikode",          "doctors": [("Dr. Aswin Joseph", "Neurology", 910, 14), ("Dr. Shilpa Haridas", "General Medicine", 550, 12), ("Dr. Pradeep N.", "Orthopedics", 870, 16), ("Dr. Hiba Nizam", "Gynecology", 770, 11)]},
    {"hospital": "IQRAA International Hospital, Kozhikode",      "city": "Kozhikode",          "doctors": [("Dr. Noufal Kareem", "Cardiology", 940, 17), ("Dr. Safa Parveen", "Pediatrics", 630, 8), ("Dr. Ameen Basheer", "Urology", 860, 13), ("Dr. Roshni Das", "Dermatology", 705, 9)]},
    {"hospital": "Jubilee Mission Medical College, Thrissur",    "city": "Thrissur",           "doctors": [("Dr. Mithun Varma", "Cardiology", 930, 16), ("Dr. Ann Maria Joseph", "Oncology", 1090, 17), ("Dr. Rakesh C. Menon", "Orthopedics", 890, 15), ("Dr. Divya Rajan", "Ophthalmology", 680, 10)]},
    {"hospital": "Sun Medical and Research Centre, Thrissur",    "city": "Thrissur",           "doctors": [("Dr. Adarsh Mohan", "General Medicine", 520, 8), ("Dr. Nimmy George", "Endocrinology", 810, 12), ("Dr. Shyam Balakrishnan", "Gastroenterology", 840, 11), ("Dr. Merin Thomas", "ENT", 610, 9)]},
    {"hospital": "Caritas Hospital, Kottayam",                   "city": "Kottayam",           "doctors": [("Dr. Georgekutty Paul", "Nephrology", 930, 18), ("Dr. Athira James", "Gynecology", 760, 10), ("Dr. Joel Kurian", "Psychiatry", 740, 11), ("Dr. Manju Mathew", "Pediatrics", 650, 12)]},
    {"hospital": "Believers Church Medical College, Thiruvalla", "city": "Thiruvalla",         "doctors": [("Dr. Sijin Philip", "Pulmonology", 780, 13), ("Dr. Riya Susan Thomas", "Dermatology", 700, 8), ("Dr. Binesh Varghese", "Urology", 855, 14), ("Dr. Anju Mariam", "Oncology", 1040, 16)]},
    {"hospital": "Pushpagiri Medical College, Thiruvalla",       "city": "Thiruvalla",         "doctors": [("Dr. Albin Chacko", "Cardiology", 925, 15), ("Dr. Greeshma Nair", "Neurology", 905, 13), ("Dr. Faisal Ahamed", "General Medicine", 530, 9), ("Dr. Lekha Kurup", "Ophthalmology", 660, 11)]},
]


# ── DATABASE MODELS ───────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    phone    = db.Column(db.String(20))
    gender   = db.Column(db.String(10))
    password = db.Column(db.String(200), nullable=False)
    appointments = db.relationship("Appointment", backref="user", lazy=True)


class Doctor(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    specialty       = db.Column(db.String(100))
    fee             = db.Column(db.Integer, default=500)
    hospital        = db.Column(db.String(150), default="MediBook General Hospital")
    city            = db.Column(db.String(100), default="Chennai")
    experience      = db.Column(db.Integer, default=5)
    bio             = db.Column(db.String(400), default="Experienced specialist committed to patient-centered care.")
    portal_password = db.Column(db.String(200), default="")
    appointments    = db.relationship("Appointment", backref="doctor", lazy=True)


class Appointment(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey("user.id"),   nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    date      = db.Column(db.String(20), nullable=False)
    time      = db.Column(db.String(20), nullable=False)
    reason    = db.Column(db.String(200), default="General Checkup")
    status    = db.Column(db.String(20),  default="Pending")


class DoctorBlockedSlot(db.Model):
    __table_args__ = (
        db.UniqueConstraint("doctor_id", "date", "time", name="uq_doctor_blocked_slot"),
    )
    id        = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    date      = db.Column(db.String(20), nullable=False)
    time      = db.Column(db.String(20), nullable=False)


class AppointmentMessage(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=False)
    sender_role    = db.Column(db.String(20), nullable=False)
    body           = db.Column(db.String(800), nullable=False)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
    appointment    = db.relationship(
        "Appointment",
        backref=db.backref("messages", lazy=True, cascade="all, delete-orphan"),
    )


class Hospital(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(150), unique=True, nullable=False)
    city     = db.Column(db.String(100), default="")
    password = db.Column(db.String(200), nullable=False)


# ── HELPER FUNCTIONS ──────────────────────────────────────────

def pwd_hash(plain):
    """Always use pbkdf2:sha256 — works on every platform and every werkzeug version."""
    return generate_password_hash(plain, method=HASH_METHOD)


def password_matches(stored_value, entered_value):
    """Accept current hashes and gracefully handle legacy/plain-text stored passwords."""
    stored = (stored_value or "").strip()
    entered = entered_value or ""
    if not stored or not entered:
        return False
    if "$" not in stored and ":" not in stored:
        return stored == entered
    try:
        return check_password_hash(stored, entered)
    except (ValueError, TypeError):
        return stored == entered


def verify_password_and_upgrade(record, field_name, entered_value):
    """
    Verify a password and upgrade legacy/plain-text values to the current hash format.
    Returns True when the entered password matches.
    """
    stored = getattr(record, field_name, "") or ""
    if not password_matches(stored, entered_value):
        return False
    if not stored.startswith(f"{HASH_METHOD}:"):
        setattr(record, field_name, pwd_hash(entered_value))
        db.session.commit()
    return True


def get_safe_back_url(default_endpoint):
    """Return the referrer URL only if it is from the same site and a different page."""
    fallback = url_for(default_endpoint)
    ref = request.referrer
    if not ref:
        return fallback
    try:
        ref_url = urlparse(ref)
        cur_url = urlparse(request.base_url)
        if ref_url.netloc != cur_url.netloc or ref_url.path == cur_url.path:
            return fallback
        return ref
    except ValueError:
        return fallback


def get_admin_tab_name():
    tab = request.values.get("tab", "appointments").strip().lower()
    return tab if tab in ADMIN_TABS else "appointments"

def get_doctor_tab_name():
    tab = request.values.get("tab", "appointments").strip().lower()
    return tab if tab in DOCTOR_TABS else "appointments"

def get_patient_tab_name():
    tab = request.values.get("tab", "appointments").strip().lower()
    return tab if tab in PATIENT_TABS else "appointments"

def get_hospital_tab_name():
    tab = request.values.get("tab", "appointments").strip().lower()
    return tab if tab in HOSPITAL_TABS else "appointments"


def redirect_to_admin_tab(tab):
    return redirect(url_for("admin_dashboard", tab=tab if tab in ADMIN_TABS else "appointments"))

def redirect_to_doctor_tab(tab, **kwargs):
    params = {"tab": tab if tab in DOCTOR_TABS else "appointments"}
    params.update({k: v for k, v in kwargs.items() if v not in {None, ""}})
    return redirect(url_for("doctor_dashboard", **params))

def redirect_to_patient_tab(tab, **kwargs):
    params = {"tab": tab if tab in PATIENT_TABS else "appointments"}
    params.update({k: v for k, v in kwargs.items() if v not in {None, ""}})
    return redirect(url_for("patient_dashboard", **params))

def redirect_to_hospital_tab(tab, **kwargs):
    params = {"tab": tab if tab in HOSPITAL_TABS else "appointments"}
    params.update({k: v for k, v in kwargs.items() if v not in {None, ""}})
    return redirect(url_for("hospital_dashboard", **params))


def order_time_slots(slots):
    """Sort a collection of time strings into the canonical ALL_TIME_SLOTS order."""
    unique = set(slots)
    return [s for s in ALL_TIME_SLOTS if s in unique]


def get_booked_times(doctor_id, appt_date):
    if not doctor_id or not appt_date:
        return []
    booked = Appointment.query.filter_by(doctor_id=doctor_id, date=appt_date).filter(
        Appointment.status.in_(["Pending", "Approved"])
    ).all()
    return order_time_slots(a.time for a in booked)

def get_pending_times(doctor_id, appt_date):
    if not doctor_id or not appt_date:
        return []
    rows = Appointment.query.filter_by(doctor_id=doctor_id, date=appt_date, status="Pending").all()
    return order_time_slots(a.time for a in rows)

def get_approved_times(doctor_id, appt_date):
    if not doctor_id or not appt_date:
        return []
    rows = Appointment.query.filter_by(doctor_id=doctor_id, date=appt_date, status="Approved").all()
    return order_time_slots(a.time for a in rows)

def get_blocked_times(doctor_id, slot_date):
    if not doctor_id or not slot_date:
        return []
    rows = DoctorBlockedSlot.query.filter_by(doctor_id=doctor_id, date=slot_date).all()
    return order_time_slots(s.time for s in rows)


def build_slot_rows(doctor_id, slot_date):
    """Return a list of slot dicts (time, status, label, action) for the availability tab."""
    booked  = set(get_booked_times(doctor_id, slot_date))
    blocked = set(get_blocked_times(doctor_id, slot_date))
    rows = []
    for slot in ALL_TIME_SLOTS:
        if slot in booked:
            rows.append({"time": slot, "status": "booked",  "label": "Booked by patient",  "action": ""})
        elif slot in blocked:
            rows.append({"time": slot, "status": "blocked", "label": "Marked unavailable", "action": "open"})
        else:
            rows.append({"time": slot, "status": "open",    "label": "Open for booking",   "action": "block"})
    return rows


def get_selected_appointment(appointments, requested_id):
    """Find an appointment by ID from a list, or fall back to the first one."""
    if not appointments:
        return None
    if requested_id:
        for appt in appointments:
            if appt.id == requested_id:
                return appt
    return appointments[0]


def can_patient_cancel_appointment(appt):
    """Patients may cancel only while the appointment is still pending."""
    if not appt:
        return False
    return (appt.status or "").strip().lower() == "pending"


def delete_doctor_with_appointments(doc):
    """Remove a doctor and all their linked appointments and messages."""
    appts = Appointment.query.filter_by(doctor_id=doc.id).all()
    ids   = [a.id for a in appts]
    if ids:
        AppointmentMessage.query.filter(AppointmentMessage.appointment_id.in_(ids)).delete(synchronize_session=False)
        Appointment.query.filter(Appointment.id.in_(ids)).delete(synchronize_session=False)
    DoctorBlockedSlot.query.filter_by(doctor_id=doc.id).delete(synchronize_session=False)
    db.session.delete(doc)
    return len(ids)


def delete_patient_with_appointments(user):
    """Remove a patient and all their linked appointments and messages."""
    appts = Appointment.query.filter_by(user_id=user.id).all()
    ids   = [a.id for a in appts]
    if ids:
        AppointmentMessage.query.filter(AppointmentMessage.appointment_id.in_(ids)).delete(synchronize_session=False)
        Appointment.query.filter(Appointment.id.in_(ids)).delete(synchronize_session=False)
    db.session.delete(user)
    return len(ids)


def build_seed_records():
    """Combine TN base seeds with Kerala group seeds into one flat list."""
    records = list(BASE_DOCTOR_SEEDS)
    for group in KERALA_DOCTOR_GROUPS:
        for name, specialty, fee, exp in group["doctors"]:
            bio_template = SPECIALTY_BIOS.get(specialty, "Experienced specialist providing reliable outpatient and follow-up care at {hospital}.")
            records.append({
                "name": name, "specialty": specialty, "fee": fee,
                "hospital": group["hospital"], "city": group["city"], "experience": exp,
                "bio": bio_template.format(city=group["city"], hospital=group["hospital"]),
            })
    return records


def seed_default_doctors():
    """Insert seed doctors that don't already exist in the database."""
    default_hash = pwd_hash(DEFAULT_DOCTOR_PASSWORD)
    existing = {
        (name, hospital, city)
        for name, hospital, city in db.session.query(Doctor.name, Doctor.hospital, Doctor.city).all()
    }
    new_doctors = []
    for rec in build_seed_records():
        key = (rec["name"], rec["hospital"], rec["city"])
        if key not in existing:
            new_doctors.append(Doctor(**rec, portal_password=default_hash))
            existing.add(key)
    if new_doctors:
        db.session.add_all(new_doctors)
        db.session.commit()
    return len(new_doctors)


def ensure_doctor_portal_schema():
    """Add the portal_password column if missing, then set default passwords."""
    inspector = inspect(db.engine)
    columns = {col["name"] for col in inspector.get_columns("doctor")}
    if "portal_password" not in columns:
        db.session.execute(text("ALTER TABLE doctor ADD COLUMN portal_password VARCHAR(200) DEFAULT ''"))
        db.session.commit()
    default_hash = pwd_hash(DEFAULT_DOCTOR_PASSWORD)
    for doc in Doctor.query.all():
        if not (doc.portal_password or "").strip():
            doc.portal_password = default_hash
    db.session.commit()


def ensure_hospital_schema():
    """Create one Hospital login account per unique hospital name in the Doctor table."""
    default_hash = pwd_hash(DEFAULT_HOSPITAL_PASSWORD)
    existing_names = {h.name for h in Hospital.query.all()}

    hospital_pairs = (
        db.session.query(Doctor.hospital, Doctor.city)
        .filter(Doctor.hospital != None, Doctor.hospital != "")
        .distinct()
        .all()
    )

    new_hospitals = []
    for hosp_name, hosp_city in hospital_pairs:
        if hosp_name and hosp_name not in existing_names:
            new_hospitals.append(Hospital(name=hosp_name, city=hosp_city or "", password=default_hash))
            existing_names.add(hosp_name)

    if new_hospitals:
        db.session.add_all(new_hospitals)
        db.session.commit()


# ── ROUTES ────────────────────────────────────────────────────

@app.route("/")
def home():
    if not session.get("role"):
        return redirect(url_for("login"))
    doctors     = Doctor.query.all()
    specialties = sorted(set(d.specialty for d in doctors if d.specialty))
    cities      = sorted(set(d.city      for d in doctors if d.city))
    hospitals   = sorted(set(d.hospital  for d in doctors if d.hospital))
    return render_template("home.html", doctors=doctors,
                           specialties=specialties, cities=cities, hospitals=hospitals)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        phone    = request.form.get("phone", "").strip()
        gender   = request.form.get("gender", "")
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not name or not email or not password:
            flash("Please fill all required fields.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("This email is already registered. Please login.", "error")
        else:
            # pwd_hash uses pbkdf2:sha256 — consistent across all platforms
            db.session.add(User(
                name=name, email=email, phone=phone, gender=gender,
                password=pwd_hash(password),
            ))
            db.session.commit()
            flash("Registration successful. You can login now.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    doctors   = Doctor.query.order_by(Doctor.name).all()
    hospitals = Hospital.query.order_by(Hospital.name).all()

    # For GET: read role from query string to pre-select the tab
    # For POST: read role from form body (request.form) — NOT request.values,
    #           because request.values gives GET params priority over POST params,
    #           which would cause the wrong login branch to run if the URL had a
    #           stale ?login_role= query param.
    if request.method == "POST":
        selected_role = request.form.get("login_role", "patient").strip().lower()
    else:
        selected_role = request.args.get("login_role", "patient").strip().lower()

    if selected_role not in {"patient", "doctor", "admin", "hospital"}:
        selected_role = "patient"

    if request.method == "POST":
        password = request.form.get("password", "")

        if selected_role == "hospital":
            hosp_id = request.form.get("hospital_id", "").strip()
            hosp    = db.session.get(Hospital, int(hosp_id)) if hosp_id.isdigit() else None
            if hosp and verify_password_and_upgrade(hosp, "password", password):
                session.clear()
                session.update({"role": "hospital", "hospital_id": hosp.id, "name": hosp.name})
                flash(f"Welcome, {hosp.name}!", "success")
                return redirect(url_for("hospital_dashboard"))
            flash("Incorrect hospital selection or password.", "error")

        elif selected_role == "admin":
            email = request.form.get("email", "").strip().lower()
            if email == "admin@medibook.com" and password == "admin123":
                session.clear()
                session.update({"role": "admin", "name": "Administrator"})
                flash("Welcome, Admin!", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Incorrect admin email or password.", "error")

        elif selected_role == "doctor":
            doc_id = request.form.get("doctor_id", "").strip()
            doctor = db.session.get(Doctor, int(doc_id)) if doc_id.isdigit() else None
            if doctor and verify_password_and_upgrade(doctor, "portal_password", password):
                session.clear()
                session.update({"role": "doctor", "doctor_id": doctor.id, "name": doctor.name})
                flash(f"Welcome, {doctor.name}!", "success")
                return redirect(url_for("doctor_dashboard"))
            flash("Incorrect doctor selection or password.", "error")

        else:  # patient
            email = request.form.get("email", "").strip().lower()
            user  = User.query.filter_by(email=email).first()
            if user and verify_password_and_upgrade(user, "password", password):
                session.clear()
                session.update({"role": "user", "user_id": user.id, "name": user.name})
                flash(f"Welcome back, {user.name}!", "success")
                return redirect(url_for("home"))
            if not user:
                flash("No patient account was found for that email. Please register first.", "error")
            else:
                flash("Incorrect email or password.", "error")

    return render_template("login.html", doctors=doctors, hospitals=hospitals, selected_role=selected_role)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ── PATIENT ROUTES ────────────────────────────────────────────

@app.route("/dashboard")
def patient_dashboard():
    if session.get("role") != "user":
        flash("Please login to continue.", "error")
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        flash("Your account could not be found. Please login again.", "error")
        return redirect(url_for("login"))

    active_tab    = get_patient_tab_name()
    req_msg_id    = request.values.get("appointment_id", "").strip()
    req_msg_id    = int(req_msg_id) if req_msg_id.isdigit() else None
    appts         = Appointment.query.filter_by(user_id=user.id).order_by(Appointment.id.desc()).all()
    msg_appts     = [a for a in appts if a.doctor]
    selected_appt = get_selected_appointment(msg_appts, req_msg_id)
    selected_msgs = sorted(selected_appt.messages, key=lambda m: m.created_at or datetime.min) if selected_appt else []

    counts = {
        "total":           len(appts),
        "pending":         sum(1 for a in appts if a.status == "Pending"),
        "approved":        sum(1 for a in appts if a.status == "Approved"),
        "completed":       sum(1 for a in appts if a.status == "Completed"),
        "cancelled":       sum(1 for a in appts if a.status == "Cancelled"),
        "message_threads": len(msg_appts),
    }
    return render_template("patient_dashboard.html",
        user=user, appointments=appts, counts=counts, active_tab=active_tab,
        message_appointments=msg_appts, selected_message_appointment=selected_appt,
        selected_messages=selected_msgs)


@app.route("/book", methods=["GET", "POST"])
def book():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    doctors    = Doctor.query.order_by(Doctor.name).all()
    today      = date.today().isoformat()
    preselect  = request.values.get("doc", "").strip()
    back_url   = get_safe_back_url("patient_dashboard")
    sel_doctor = next((d for d in doctors if str(d.id) == preselect), None)
    if not sel_doctor:
        preselect = ""

    def render_book(**extra):
        return render_template("book.html", doctors=doctors, today=today,
                               preselect_id=preselect, back_url=back_url,
                               selected_doctor=sel_doctor, **extra)

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", "").strip()
        appt_date = request.form.get("date", "").strip()
        appt_time = request.form.get("time", "").strip()

        if not doctor_id or not appt_date or not appt_time:
            flash("Please select a doctor, date, and time slot.", "error")
            return render_book()
        if not doctor_id.isdigit():
            flash("Please choose a valid doctor.", "error")
            return render_book()

        doctor = db.session.get(Doctor, int(doctor_id))
        if not doctor:
            flash("That doctor could not be found.", "error")
            return render_book()

        booked  = set(get_booked_times(doctor.id, appt_date))
        blocked = set(get_blocked_times(doctor.id, appt_date))
        if appt_time in booked:
            flash("That time slot is already taken. Please choose another.", "error")
            return render_book()
        if appt_time in blocked:
            flash("That time slot is marked unavailable by the doctor.", "error")
            return render_book()

        db.session.add(Appointment(
            user_id=session["user_id"], doctor_id=doctor.id,
            date=appt_date, time=appt_time, reason="General Checkup",
        ))
        db.session.commit()
        flash("Appointment booked successfully.", "success")
        return redirect(url_for("patient_dashboard"))

    return render_book()


@app.route("/cancel/<int:appt_id>", methods=["POST"])
def cancel_appointment(appt_id):
    if session.get("role") != "user":
        return redirect(url_for("login"))
    appt = Appointment.query.get_or_404(appt_id)
    if appt.user_id != session["user_id"]:
        flash("You cannot cancel someone else's appointment.", "error")
    elif can_patient_cancel_appointment(appt):
        appt.status = "Cancelled"
        db.session.commit()
        flash("Appointment cancelled.", "success")
    else:
        flash("This appointment can no longer be cancelled.", "error")
    return redirect(url_for("patient_dashboard"))


@app.route("/patient/messages/send", methods=["POST"])
def patient_send_message():
    if session.get("role") != "user":
        flash("Please login to continue.", "error")
        return redirect(url_for("login"))

    appt_id = request.form.get("appointment_id", "").strip()
    body    = request.form.get("body", "").strip()
    if not appt_id.isdigit():
        flash("Please choose an appointment before sending a message.", "error")
        return redirect_to_patient_tab("messages")

    appt = Appointment.query.get_or_404(int(appt_id))
    if appt.user_id != session.get("user_id"):
        flash("You cannot message on someone else's appointment.", "error")
        return redirect_to_patient_tab("messages")
    if not body:
        flash("Message cannot be empty.", "error")
        return redirect_to_patient_tab("messages", appointment_id=appt.id)

    db.session.add(AppointmentMessage(appointment_id=appt.id, sender_role="patient", body=body))
    db.session.commit()
    flash("Message sent to the doctor.", "success")
    return redirect_to_patient_tab("messages", appointment_id=appt.id)


# ── DOCTOR ROUTES ─────────────────────────────────────────────

@app.route("/doctor")
def doctor_dashboard():
    if session.get("role") != "doctor":
        flash("Doctor access only.", "error")
        return redirect(url_for("login"))

    doctor = db.session.get(Doctor, session.get("doctor_id"))
    if not doctor:
        session.clear()
        flash("Doctor account could not be found. Please login again.", "error")
        return redirect(url_for("login"))

    active_tab    = get_doctor_tab_name()
    sel_date      = request.values.get("date", "").strip() or date.today().isoformat()
    req_msg_id    = request.values.get("appointment_id", "").strip()
    req_msg_id    = int(req_msg_id) if req_msg_id.isdigit() else None
    appts         = Appointment.query.filter_by(doctor_id=doctor.id).order_by(
                        Appointment.date.desc(), Appointment.id.desc()).all()
    msg_appts     = [a for a in appts if a.user]
    selected_appt = get_selected_appointment(msg_appts, req_msg_id)
    selected_msgs = sorted(selected_appt.messages, key=lambda m: m.created_at or datetime.min) if selected_appt else []
    slot_rows     = build_slot_rows(doctor.id, sel_date)

    counts = {
        "total":         len(appts),
        "pending":       sum(1 for a in appts if a.status == "Pending"),
        "approved":      sum(1 for a in appts if a.status == "Approved"),
        "completed":     sum(1 for a in appts if a.status == "Completed"),
        "messages":      sum(len(a.messages) for a in msg_appts),
        "blocked_today": sum(1 for r in slot_rows if r["status"] == "blocked"),
    }
    return render_template("doctor_dashboard.html",
        doctor=doctor, appointments=appts, active_tab=active_tab,
        counts=counts, selected_date=sel_date, slot_rows=slot_rows,
        message_appointments=msg_appts, selected_message_appointment=selected_appt,
        selected_messages=selected_msgs)


@app.route("/doctor/availability", methods=["POST"])
def update_doctor_availability():
    if session.get("role") != "doctor":
        flash("Doctor access only.", "error")
        return redirect(url_for("login"))

    doctor = db.session.get(Doctor, session.get("doctor_id"))
    if not doctor:
        session.clear()
        flash("Doctor account could not be found.", "error")
        return redirect(url_for("login"))

    slot_date = request.form.get("date", "").strip()
    slot_time = request.form.get("time", "").strip()
    action    = request.form.get("action", "").strip().lower()

    if not slot_date or slot_time not in ALL_TIME_SLOTS:
        flash("Choose a valid date and time slot.", "error")
        return redirect_to_doctor_tab("availability", date=slot_date or date.today().isoformat())
    if slot_date < date.today().isoformat():
        flash("Availability can only be changed for today or future dates.", "error")
        return redirect_to_doctor_tab("availability", date=slot_date)
    if slot_time in set(get_booked_times(doctor.id, slot_date)):
        flash("Booked slots cannot be edited from availability.", "error")
        return redirect_to_doctor_tab("availability", date=slot_date)

    existing = DoctorBlockedSlot.query.filter_by(doctor_id=doctor.id, date=slot_date, time=slot_time).first()
    if action == "block" and not existing:
        db.session.add(DoctorBlockedSlot(doctor_id=doctor.id, date=slot_date, time=slot_time))
        db.session.commit()
        flash(f"{slot_time} is now unavailable on {slot_date}.", "success")
    elif action == "open" and existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f"{slot_time} is now open for booking on {slot_date}.", "success")
    elif action not in {"block", "open"}:
        flash("Unknown availability action.", "error")
    else:
        flash(f"{slot_time} is now {'unavailable' if action == 'block' else 'open'} on {slot_date}.", "success")

    return redirect_to_doctor_tab("availability", date=slot_date)


@app.route("/doctor/appointment/<int:appt_id>/<action>", methods=["POST"])
def doctor_appointment_action(appt_id, action):
    if session.get("role") != "doctor":
        flash("Doctor access only.", "error")
        return redirect(url_for("login"))

    doctor = db.session.get(Doctor, session.get("doctor_id"))
    if not doctor:
        session.clear()
        flash("Doctor account could not be found.", "error")
        return redirect(url_for("login"))

    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doctor.id:
        flash("You cannot manage another doctor's appointments.", "error")
        return redirect_to_doctor_tab("appointments")

    if action in {"approve", "reject", "complete"}:
        if not db.session.get(User, appt.user_id):
            flash("Appointment data is incomplete.", "error")
            return redirect_to_doctor_tab("appointments")
        if action == "approve":
            appt.status = "Approved"
        elif action == "reject":
            appt.status = "Rejected"
        elif appt.status != "Approved":
            flash("Only approved appointments can be marked completed.", "error")
            return redirect_to_doctor_tab("appointments")
        else:
            appt.status = "Completed"
        db.session.commit()
        flash(f"Appointment {appt.status.lower()}.", "success")
    else:
        flash("Unknown doctor action.", "error")

    return redirect_to_doctor_tab("appointments")


@app.route("/doctor/messages/send", methods=["POST"])
def doctor_send_message():
    if session.get("role") != "doctor":
        flash("Doctor access only.", "error")
        return redirect(url_for("login"))

    appt_id = request.form.get("appointment_id", "").strip()
    body    = request.form.get("body", "").strip()
    if not appt_id.isdigit():
        flash("Please choose an appointment before sending a message.", "error")
        return redirect_to_doctor_tab("messages")

    appt = Appointment.query.get_or_404(int(appt_id))
    if appt.doctor_id != session.get("doctor_id"):
        flash("You cannot message on someone else's appointment.", "error")
        return redirect_to_doctor_tab("messages")
    if not body:
        flash("Message cannot be empty.", "error")
        return redirect_to_doctor_tab("messages", appointment_id=appt.id)

    db.session.add(AppointmentMessage(appointment_id=appt.id, sender_role="doctor", body=body))
    db.session.commit()
    flash("Message sent to the patient.", "success")
    return redirect_to_doctor_tab("messages", appointment_id=appt.id)


# ── AJAX ──────────────────────────────────────────────────────

@app.route("/get-booked-slots")
def get_booked_slots():
    doctor_id = request.args.get("doctor_id")
    appt_date = request.args.get("date")
    if not doctor_id or not str(doctor_id).isdigit() or not appt_date:
        return jsonify({"booked": [], "blocked": [], "unavailable": []})

    doctor_id   = int(doctor_id)
    pending     = get_pending_times(doctor_id, appt_date)
    approved    = get_approved_times(doctor_id, appt_date)
    blocked     = get_blocked_times(doctor_id, appt_date)
    booked      = order_time_slots(list(pending) + list(approved))
    unavailable = order_time_slots(list(booked) + list(blocked))
    return jsonify({"booked": booked, "pending": pending, "approved": approved,
                    "blocked": blocked, "unavailable": unavailable})


# ── ADMIN ROUTES ──────────────────────────────────────────────

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))

    active_tab   = get_admin_tab_name()
    appointments = Appointment.query.order_by(Appointment.id.desc()).all()
    patients     = User.query.order_by(User.id.desc()).all()
    doctors      = Doctor.query.order_by(Doctor.name).all()
    counts = {
        "total":    len(appointments),
        "pending":  sum(1 for a in appointments if a.status == "Pending"),
        "approved": sum(1 for a in appointments if a.status == "Approved"),
        "completed": sum(1 for a in appointments if a.status == "Completed"),
        "patients": len(patients),
        "doctors":  len(doctors),
    }
    return render_template("admin_dashboard.html",
        appointments=appointments, patients=patients,
        doctors=doctors, counts=counts, active_tab=active_tab)


@app.route("/admin/appointment/<int:appt_id>/<action>", methods=["POST"])
def admin_appointment_action(appt_id, action):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    active_tab = get_admin_tab_name()
    appt = Appointment.query.get_or_404(appt_id)
    if action == "delete":
        db.session.delete(appt)
        db.session.commit()
        flash("Appointment deleted.", "success")
    else:
        flash("Unknown admin action.", "error")
    return redirect_to_admin_tab(active_tab)


@app.route("/admin/add-doctor", methods=["POST"])
def add_doctor():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    name       = request.form.get("name", "").strip()
    specialty  = request.form.get("specialty", "")
    fee        = request.form.get("fee", "500")
    hospital   = request.form.get("hospital", "MediBook General Hospital").strip()
    city       = request.form.get("city", "Chennai").strip()
    experience = request.form.get("experience", "5")
    bio        = request.form.get("bio", "Experienced specialist.").strip()

    if not name:
        flash("Doctor name is required.", "error")
        return redirect_to_admin_tab("doctors")

    db.session.add(Doctor(
        name=name, specialty=specialty,
        fee=int(fee) if fee.isdigit() else 500,
        hospital=hospital, city=city,
        experience=int(experience) if experience.isdigit() else 5,
        bio=bio, portal_password=pwd_hash(DEFAULT_DOCTOR_PASSWORD),
    ))
    db.session.commit()

    # Also create a hospital account if this hospital is new
    if hospital and not Hospital.query.filter_by(name=hospital).first():
        db.session.add(Hospital(name=hospital, city=city, password=pwd_hash(DEFAULT_HOSPITAL_PASSWORD)))
        db.session.commit()

    flash(f"Dr. {name} added successfully!", "success")
    return redirect_to_admin_tab("doctors")


@app.route("/admin/delete-doctor/<int:doc_id>", methods=["POST"])
def delete_doctor(doc_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    active_tab = get_admin_tab_name()
    doc = Doctor.query.get_or_404(doc_id)
    count = delete_doctor_with_appointments(doc)
    db.session.commit()
    msg = f"Dr. {doc.name} and {count} linked appointment(s) were removed." if count else f"Dr. {doc.name} removed."
    flash(msg, "success")
    return redirect_to_admin_tab(active_tab)


@app.route("/admin/delete-patient/<int:user_id>", methods=["POST"])
def delete_patient(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    active_tab = get_admin_tab_name()
    user = User.query.get_or_404(user_id)
    count = delete_patient_with_appointments(user)
    db.session.commit()
    msg = f"{user.name} and {count} linked appointment(s) were deleted." if count else f"{user.name} deleted."
    flash(msg, "success")
    return redirect_to_admin_tab(active_tab)


@app.route("/admin/delete-all/<target>", methods=["POST"])
def delete_all_admin_records(target):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    active_tab = get_admin_tab_name()

    if target == "appointments":
        count = Appointment.query.count()
        if not count:
            flash("No appointments to delete.", "error")
            return redirect_to_admin_tab(active_tab)
        AppointmentMessage.query.delete(synchronize_session=False)
        Appointment.query.delete(synchronize_session=False)
        db.session.commit()
        flash(f"Deleted all {count} appointment(s).", "success")

    elif target == "doctors":
        count = Doctor.query.count()
        if not count:
            flash("No doctors to delete.", "error")
            return redirect_to_admin_tab(active_tab)
        appt_count = Appointment.query.count()
        AppointmentMessage.query.delete(synchronize_session=False)
        Appointment.query.delete(synchronize_session=False)
        DoctorBlockedSlot.query.delete(synchronize_session=False)
        Doctor.query.delete(synchronize_session=False)
        db.session.commit()
        flash(f"Deleted all {count} doctor(s) and {appt_count} linked appointment(s).", "success")

    elif target == "patients":
        count = User.query.count()
        if not count:
            flash("No patients to delete.", "error")
            return redirect_to_admin_tab(active_tab)
        appt_count = Appointment.query.count()
        AppointmentMessage.query.delete(synchronize_session=False)
        Appointment.query.delete(synchronize_session=False)
        User.query.delete(synchronize_session=False)
        db.session.commit()
        flash(f"Deleted all {count} patient account(s) and {appt_count} linked appointment(s).", "success")

    else:
        flash("Unknown delete-all target.", "error")

    return redirect_to_admin_tab(active_tab)


# ── HOSPITAL ROUTES ───────────────────────────────────────────

@app.route("/hospital")
def hospital_dashboard():
    if session.get("role") != "hospital":
        flash("Hospital access only.", "error")
        return redirect(url_for("login"))

    hospital = db.session.get(Hospital, session.get("hospital_id"))
    if not hospital:
        session.clear()
        flash("Hospital account could not be found. Please login again.", "error")
        return redirect(url_for("login"))

    active_tab = get_hospital_tab_name()
    doctors    = Doctor.query.filter_by(hospital=hospital.name).order_by(Doctor.name).all()
    doctor_ids = [d.id for d in doctors]

    appointments = []
    if doctor_ids:
        appointments = Appointment.query.filter(
            Appointment.doctor_id.in_(doctor_ids)
        ).order_by(Appointment.date.desc(), Appointment.id.desc()).all()

    counts = {
        "total":    len(appointments),
        "pending":  sum(1 for a in appointments if a.status == "Pending"),
        "approved": sum(1 for a in appointments if a.status == "Approved"),
        "completed": sum(1 for a in appointments if a.status == "Completed"),
        "doctors":  len(doctors),
    }
    return render_template("hospital_dashboard.html",
        hospital=hospital, doctors=doctors,
        appointments=appointments, counts=counts,
        active_tab=active_tab)


# ── APP STARTUP ───────────────────────────────────────────────

with app.app_context():
    db.create_all()
    ensure_doctor_portal_schema()
    added = seed_default_doctors()
    if added:
        print(f"Added {added} seeded doctor(s). Total: {Doctor.query.count()}")
    ensure_hospital_schema()

if __name__ == "__main__":
    app.run(debug=True)
