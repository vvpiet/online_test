import os
import json
import random
import string
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from passlib.context import CryptContext
from sqlalchemy import select, func, and_

from db import DBSession, init_db
from models import (
    Base,
    User,
    QuestionPaper,
    MCQQuestion,
    ExamSession,
    IPConfig,
    TimetableEntry,
    AppConfig,
)

BRANCHES = [
    ("CIVIL", "11191"),
    ("AI&DS", "11995"),
    ("ARTIFICIAL INTELLIGENCE & DS", "11263"),
    ("CSE", "11242"),
    ("ELECTRICAL", "11293"),
    ("E&TC", "11372"),
    ("MECHANICAL", "11216"),
    ("BCA", "11101"),
    ("MCA", "22241"),
    ("M.tech (CSE)", "12242"),
    ("M.tech (Design)", "12601"),
]
CLASSES = ["FY", "SY", "TY", "B.Tech", "BCA", "MCA", "M.tech (CSE)", "M.tech (Design)"]
SEMESTERS = [str(i) for i in range(1, 9)]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def generate_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def init_app_db():
    init_db(Base)
    with DBSession() as db:
        existing_admin = db.execute(select(User).where(User.role == "admin")).scalars().first()
        if not existing_admin:
            admin = User(
                prn="admin",
                name="Administrator",
                password_hash=hash_password("admin123"),
                role="admin",
                branch="ADMIN",
                branch_code="00000",
                student_class="ADMIN",
                semester="0",
            )
            db.add(admin)
            st.success("Default admin created: username=admin password=admin123. Please change this password.")
        existing_config = db.execute(select(AppConfig)).scalars().first()
        if not existing_config:
            db.add(AppConfig(countdown_minutes=30))
        if not db.execute(select(IPConfig)).scalars().first():
            db.add(IPConfig(allowed_ips=""))


def get_active_paper_for_student(db, branch_code, semester):
    now = datetime.utcnow()
    stmt = (
        select(QuestionPaper)
        .join(TimetableEntry)
        .where(
            QuestionPaper.branch_code == branch_code,
            QuestionPaper.semester == semester,
            TimetableEntry.start_at <= now,
            TimetableEntry.end_at >= now,
        )
        .order_by(TimetableEntry.start_at.desc())
    )
    return db.execute(stmt).scalars().first()


def parse_question_file(uploaded_file):
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read uploaded file: {exc}")
        return None

    required_columns = {"question", "option_a", "option_b", "option_c", "option_d", "answer_key"}
    if not required_columns.issubset({c.lower() for c in df.columns}):
        st.error("Upload must contain columns: question, option_a, option_b, option_c, option_d, answer_key")
        return None

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "text": str(row["question"]).strip(),
                "option_a": str(row["option_a"]).strip(),
                "option_b": str(row["option_b"]).strip(),
                "option_c": str(row["option_c"]).strip(),
                "option_d": str(row["option_d"]).strip(),
                "answer_key": str(row["answer_key"]).strip().lower(),
            }
        )
    return records


def render_proctoring_component():
    js = """
    <div id='proctoring'>
      <p><strong>Proctoring active:</strong> camera and tab switch monitoring enabled.</p>
      <video id='camera' autoplay playsinline style='width:100%;max-width:460px;border:1px solid #ddd;border-radius:8px;'></video>
      <p id='tabstatus' style='color:#d30;'>Watching for tab switches...</p>
      <script>
        async function startCamera() {
          try {
            const stream = await navigator.mediaDevices.getUserMedia({video:true, audio:false});
            const video = document.getElementById('camera');
            video.srcObject = stream;
          } catch (err) {
            document.getElementById('tabstatus').innerText = 'Camera access denied. Please allow camera for proctoring.';
          }
        }
        document.addEventListener('visibilitychange', () => {
          const status = document.getElementById('tabstatus');
          if (document.hidden) {
            status.innerText = 'Tab switch detected. Please return to the test window immediately.';
            status.style.color = '#d30';
          } else {
            status.innerText = 'Back to test window.';
            status.style.color = '#2a7';
          }
        });
        startCamera();
      </script>
    </div>
    """
    st.components.v1.html(js, height=400)


def get_client_ip():
    html = """
    <script>
      async function fetchIp() {
        try {
          const resp = await fetch('https://api.ipify.org?format=json');
          const data = await resp.json();
          const el = document.getElementById('client_ip');
          if (el) el.value = data.ip;
        } catch (e) {
          console.log(e);
        }
      }
      fetchIp();
    </script>
    """
    st.text_input("Current browser IP", value="", key="client_ip", disabled=True)
    st.components.v1.html(html, height=0)
    return st.session_state.get("client_ip", "")


def admin_panel():
    st.header("Admin Panel")

    with DBSession() as db:
        config = db.execute(select(AppConfig)).scalars().first()
        ipconfig = db.execute(select(IPConfig)).scalars().first()

        st.subheader("IP Address Configuration")
        allowed_ips = st.text_area(
            "Allowed IP addresses (one per line or comma-separated)",
            value=ipconfig.allowed_ips if ipconfig else "",
            height=120,
        )
        if st.button("Save IP configuration"):
            if ipconfig:
                ipconfig.allowed_ips = allowed_ips.strip()
                ipconfig.updated_at = datetime.utcnow()
                db.add(ipconfig)
            else:
                db.add(IPConfig(allowed_ips=allowed_ips.strip()))
            st.success("IP configuration saved.")

        st.subheader("Exam Timer Configuration")
        minutes = st.number_input("Exam duration in minutes", min_value=30, max_value=90, value=config.countdown_minutes if config else 30)
        if st.button("Save timer"):
            if config:
                config.countdown_minutes = minutes
                config.last_updated = datetime.utcnow()
                db.add(config)
            else:
                db.add(AppConfig(countdown_minutes=minutes))
            st.success("Timer saved.")

        st.subheader("Upload Question Paper")
        with st.form("upload_questions"):
            title = st.text_input("Paper title", "Sample MCQ Paper")
            branch_label = st.selectbox("Branch", [b[0] for b in BRANCHES])
            branch_code = dict(BRANCHES)[branch_label]
            semester = st.selectbox("Semester", SEMESTERS)
            file = st.file_uploader("Upload CSV or Excel with columns: question, option_a, option_b, option_c, option_d, answer_key", type=["csv", "xlsx", "xls"])
            submit_upload = st.form_submit_button("Upload Questions")
        if submit_upload and file is not None:
            records = parse_question_file(file)
            if records is not None:
                paper = QuestionPaper(title=title, branch=branch_label, branch_code=branch_code, semester=semester, active=True)
                db.add(paper)
                db.flush()
                for record in records:
                    question = MCQQuestion(paper_id=paper.id, **record)
                    db.add(question)
                st.success(f"Uploaded {len(records)} questions for {branch_label} semester {semester}.")

        st.subheader("Manage Test Timetable")
        papers = db.execute(select(QuestionPaper).order_by(QuestionPaper.created_at.desc())).scalars().all()
        paper_map = {f"{p.title} [{p.branch}/{p.semester}]": p for p in papers}
        if paper_map:
            chosen = st.selectbox("Choose a question paper", list(paper_map.keys()))
            paper = paper_map[chosen]
            start_at = st.datetime_input("Start time (UTC)", value=datetime.utcnow())
            end_at = st.datetime_input("End time (UTC)", value=datetime.utcnow() + timedelta(hours=1))
            if st.button("Add timetable entry"):
                if end_at <= start_at:
                    st.error("End time must be after start time.")
                else:
                    entry = TimetableEntry(paper_id=paper.id, start_at=start_at, end_at=end_at)
                    db.add(entry)
                    st.success("Timetable entry created.")
        else:
            st.info("Upload a question paper first to create a timetable entry.")

        st.subheader("Student Account Management")
        with st.form("student_account"):
            prn = st.text_input("PRN number")
            name = st.text_input("Student name")
            branch_label = st.selectbox("Branch (for student)", [b[0] for b in BRANCHES], key="student_branch")
            branch_code = dict(BRANCHES)[branch_label]
            student_class = st.selectbox("Class", CLASSES)
            semester = st.selectbox("Semester", SEMESTERS, key="student_semester")
            generate_pwd = st.checkbox("Generate password now", value=True)
            password = st.text_input("Password (leave blank to generate)", type="password")
            submit_student = st.form_submit_button("Create student account")
        if submit_student:
            if not prn or not name:
                st.error("PRN and student name are required.")
            else:
                existing = db.execute(select(User).where(User.prn == prn)).scalars().first()
                if existing:
                    st.error("A student with this PRN already exists.")
                else:
                    if not password and generate_pwd:
                        password = generate_password(10)
                    if not password:
                        st.error("Provide or generate a password.")
                    else:
                        student = User(
                            prn=prn,
                            name=name,
                            password_hash=hash_password(password),
                            role="student",
                            branch=branch_label,
                            branch_code=branch_code,
                            student_class=student_class,
                            semester=semester,
                        )
                        db.add(student)
                        st.success(f"Student created. Password: {password}")

        st.subheader("Download Results")
        filter_branch = st.selectbox("Branch filter", ["All"] + [b[0] for b in BRANCHES], index=0, key="result_branch")
        filter_class = st.selectbox("Class filter", ["All"] + CLASSES, index=0, key="result_class")
        if st.button("Fetch results"):
            stmt = select(ExamSession).join(User).join(QuestionPaper)
            if filter_branch != "All":
                stmt = stmt.where(User.branch == filter_branch)
            if filter_class != "All":
                stmt = stmt.where(User.student_class == filter_class)
            results = db.execute(stmt).scalars().all()
            rows = []
            for result in results:
                rows.append(
                    {
                        "PRN": result.student.prn,
                        "Name": result.student.name,
                        "Branch": result.student.branch,
                        "Class": result.student.student_class,
                        "Semester": result.student.semester,
                        "Paper": result.paper.title if result.paper else "-",
                        "Score": result.score,
                        "Completed": result.completed,
                        "Start": result.start_time,
                        "End": result.end_time,
                    }
                )
            df = pd.DataFrame(rows)
            st.dataframe(df)
            if not df.empty:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv, "results.csv", "text/csv")


def student_panel(user):
    st.header("Student Test Portal")

    if user.active is False:
        st.error("Your account is inactive.")
        return

    with DBSession() as db:
        client_ip = get_client_ip()
        ipconfig = db.execute(select(IPConfig)).scalars().first()
        if ipconfig and ipconfig.allowed_ips:
            allowed_ips = [ip.strip() for ip in ipconfig.allowed_ips.replace(',', '\n').split() if ip.strip()]
            if client_ip:
                if client_ip not in allowed_ips:
                    st.warning("Your current IP is not among the allowed exam IP addresses. Contact admin.")
            else:
                st.info("Unable to detect IP automatically. Please ensure you are on an allowed network.")
        else:
            st.info("IP restriction is not configured by admin.")

        st.subheader("Exam selection")
        prn = user.prn
        branch_label = user.branch
        semester = user.semester
        class_label = user.student_class
        st.write(f"**PRN:** {prn}")
        st.write(f"**Name:** {user.name}")
        st.write(f"**Branch:** {branch_label}")
        st.write(f"**Class:** {class_label}")
        st.write(f"**Semester:** {semester}")

        paper = get_active_paper_for_student(db, user.branch_code, semester)
        if not paper:
            st.info("No active exam paper is available for your branch and semester right now.")
            return

        st.success(f"Active paper: {paper.title}")
        st.write("Exam will be visible and available according to the timetable.")

        can_start = True
        if client_ip and ipconfig and ipconfig.allowed_ips:
            allowed_ips = [ip.strip() for ip in ipconfig.allowed_ips.replace(',', '\n').split() if ip.strip()]
            if client_ip not in allowed_ips:
                can_start = False

        if can_start:
            if st.button("Start Exam"):
                exam_started = db.execute(
                    select(ExamSession).where(ExamSession.student_id == user.id, ExamSession.paper_id == paper.id, ExamSession.completed == False)
                ).scalars().first()
                if exam_started:
                    st.warning("You already have an in-progress exam for this paper.")
                else:
                    session = ExamSession(student_id=user.id, paper_id=paper.id, start_time=datetime.utcnow(), completed=False)
                    db.add(session)
                    st.success("Exam started. Scroll down to answer questions.")
                    st.experimental_rerun()
        else:
            st.error("Exam cannot be started from this IP address.")

        existing_session = db.execute(
            select(ExamSession).where(ExamSession.student_id == user.id, ExamSession.paper_id == paper.id, ExamSession.completed == False)
        ).scalars().first()
        if not existing_session:
            return

        countdown = config = db.execute(select(AppConfig)).scalars().first()
        duration_minutes = config.countdown_minutes if config else 30
        st.info(f"This exam is timed for {duration_minutes} minutes.")
        render_proctoring_component()

        questions = db.execute(select(MCQQuestion).where(MCQQuestion.paper_id == paper.id)).scalars().all()
        answers = {}
        if "answers" not in st.session_state:
            st.session_state.answers = {}
        with st.form("exam_form"):
            for q in questions:
                st.write(f"**Q{q.id}:** {q.text}")
                answers[q.id] = st.radio(
                    "Choose an option:",
                    ["a", "b", "c", "d"],
                    key=f"q_{q.id}",
                    index=0,
                    label_visibility="collapsed",
                )
                st.write(f"a) {q.option_a}")
                st.write(f"b) {q.option_b}")
                st.write(f"c) {q.option_c}")
                st.write(f"d) {q.option_d}")
                st.markdown("---")
            submit_exam = st.form_submit_button("Submit Exam Now")

        if submit_exam:
            score = 0
            for q in questions:
                if answers.get(q.id) == q.answer_key.lower():
                    score += 1
            existing_session.answers_json = json.dumps(answers)
            existing_session.score = score
            existing_session.completed = True
            existing_session.end_time = datetime.utcnow()
            existing_session.duration_seconds = int((existing_session.end_time - existing_session.start_time).total_seconds())
            db.add(existing_session)
            st.success(f"Exam submitted successfully. Your score: {score}/{len(questions)}")
            st.balloons()
            st.experimental_rerun()

        if existing_session.completed:
            st.success(f"You have completed this exam. Score: {existing_session.score}/{len(questions)}")
            if existing_session.answers_json:
                st.write("Your answer submissions are recorded.")


def authenticate_user(username: str, password: str):
    with DBSession() as db:
        stmt = select(User).where(User.prn == username)
        user = db.execute(stmt).scalars().first()
        if user and user.password_hash and verify_password(password, user.password_hash):
            return user
    return None


def main():
    st.set_page_config(page_title="Engineering MCQ Test Portal", layout="wide")
    init_app_db()

    st.title("Engineering College Online MCQ Test System")
    st.sidebar.title("Login")
    role = st.sidebar.selectbox("Login as", ["Student", "Admin"])
    username = st.sidebar.text_input("PRN / Admin user")
    password = st.sidebar.text_input("Password", type="password")
    login_button = st.sidebar.button("Login")

    if login_button:
        user = authenticate_user(username, password)
        if not user:
            st.error("Invalid credentials.")
            return
        if role == "Admin" and user.role != "admin":
            st.error("Admin login requires an admin user.")
            return
        if role == "Student" and user.role != "student":
            st.error("Student login requires a student account.")
            return

        st.session_state.user_id = user.id
        st.session_state.user_role = user.role
        st.session_state.user_prn = user.prn
        st.success(f"Logged in as {user.name} ({user.role}).")
        st.experimental_rerun()

    if "user_id" in st.session_state:
        with DBSession() as db:
            user = db.execute(select(User).where(User.id == st.session_state.user_id)).scalars().first()
            if user:
                if user.role == "admin":
                    admin_panel()
                else:
                    student_panel(user)
            else:
                st.error("Session user not found.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("If you need to use Postgres, set the DATABASE_URL environment variable before running the app. Example:\n`postgresql://user:password@localhost:5432/online_test`.")


if __name__ == "__main__":
    main()
