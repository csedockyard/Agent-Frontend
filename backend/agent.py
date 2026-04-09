from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from backend.models import (
    AdminAnalyticsResponse,
    AgentDecision,
    AutonomousQuiz,
    AtRiskStudent,
    CohortDistribution,
    CommunicationLog,
    CompanyRequirementRecord,
    CompanyRequirementsResponse,
    DashboardLiveInsightsResponse,
    DemoShowcaseResponse,
    DecisionCycleResponse,
    DecisionCycleSummary,
    FlightRiskAlert,
    QuizDetailResponse,
    QuizQuestion,
    SimulationActionRequest,
    SimulationActionResponse,
    SimulationActionResult,
    StudentIntervention,
    StudentJourneyData,
    StudentJourneyRecord,
    StudentJourneyResponse,
    StudentProfileSnapshot,
    TopRecommendation,
    WhatIfCompanyImpact,
    WhatIfProfileDelta,
    WhatIfTrajectoryRequest,
    WhatIfTrajectoryResponse,
)

def _resolve_db_path() -> Path:
    configured_path = os.getenv("PLACEMENTPRO_DB_PATH", "").strip()
    if configured_path:
        return Path(configured_path)
    # Vercel serverless functions can only write to /tmp at runtime.
    if os.getenv("VERCEL") == "1":
        return Path("/tmp/placementpro.db")
    repo_default = Path(__file__).resolve().parent / "placementpro.db"
    # OneDrive-synced SQLite files are prone to lock contention on Windows.
    if "onedrive" in str(repo_default).lower():
        local_app_data = Path(os.getenv("LOCALAPPDATA", str(Path.home())))
        return local_app_data / "PlacementPro" / "placementpro.db"
    return repo_default


DB_PATH = _resolve_db_path()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _from_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def _display_time(iso_time: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_time)
        return dt.astimezone().strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return iso_time


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_flag(name: str, default: str = "0") -> bool:
    return _env(name, default).lower() in {"1", "true", "yes", "on"}


def _resolve_secret(*names: str) -> str:
    for name in names:
        value = _env(name, "")
        if value and not value.startswith("REPLACE_WITH_"):
            return value
    return ""


def _external_ai_enabled() -> bool:
    return _env_flag("PLACEMENTPRO_ENABLE_EXTERNAL_AI", "0")


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout_sec: float = 6.0,
) -> dict[str, Any] | None:
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_body,
            timeout=timeout_sec,
        )
        if response.status_code >= 400:
            return None
        try:
            return response.json()
        except ValueError:
            return {}
    except requests.RequestException:
        return None


def _http_text(url: str, *, headers: dict[str, str] | None = None, timeout_sec: float = 6.0) -> str:
    try:
        response = requests.get(url, headers=headers, timeout=timeout_sec)
        if response.status_code >= 400:
            return ""
        return response.text
    except requests.RequestException:
        return ""


def _fetch_tavily_signals(company_name: str, role: str) -> list[str]:
    tavily_key = _resolve_secret("PLACEMENTPRO_TAVILY_API_KEY", "TAVILY_API_KEY", "TAVILY_KEY")
    if not tavily_key:
        return []

    payload = _http_json(
        "POST",
        "https://api.tavily.com/search",
        json_body={
            "api_key": tavily_key,
            "query": f"{company_name} campus hiring {role} skills and recruitment trends 2026",
            "max_results": 3,
            "search_depth": "basic",
        },
        timeout_sec=7.0,
    )
    if not payload:
        return []

    results = payload.get("results", [])
    signals: list[str] = []
    for item in results[:3]:
        title = str(item.get("title", "")).strip()
        content = str(item.get("content", "")).strip().replace("\n", " ")
        url = str(item.get("url", "")).strip()
        if content:
            content = content[:220]
        if title or content:
            combined = f"{title}: {content}".strip(": ")
            if url:
                combined = f"{combined} ({url})"
            signals.append(combined)
    return signals


def _fetch_jina_page_signal(url: str) -> str:
    jina_key = _resolve_secret("PLACEMENTPRO_JINA_API_KEY", "JINA_API_KEY", "JINA_KEY")
    if not jina_key or not url:
        return ""

    normalized = url.strip()
    if normalized.startswith("https://"):
        normalized = normalized[len("https://") :]
    elif normalized.startswith("http://"):
        normalized = normalized[len("http://") :]
    reader_url = f"https://r.jina.ai/http://{quote(normalized, safe=':/?=&')}"
    text = _http_text(reader_url, headers={"Authorization": f"Bearer {jina_key}"}, timeout_sec=7.0)
    return text[:350].replace("\n", " ").strip()


def _collect_company_external_context(company_name: str, role: str) -> str:
    signals = _fetch_tavily_signals(company_name, role)
    if not signals:
        return ""

    summary_parts = [f"Tavily signals: {' | '.join(signals[:2])}"]
    first_url_signal = signals[0]
    if "(" in first_url_signal and first_url_signal.endswith(")"):
        probable_url = first_url_signal[first_url_signal.rfind("(") + 1 : -1]
        jina_digest = _fetch_jina_page_signal(probable_url)
        if jina_digest:
            summary_parts.append(f"Jina digest: {jina_digest}")
    return " ".join(summary_parts)


def _call_groq_reasoner(prompt: str) -> str:
    groq_key = _resolve_secret("PLACEMENTPRO_GROQ_API_KEY", "GROQ_API_KEY", "GROK_KEY")
    if not groq_key:
        return ""

    model = _env("PLACEMENTPRO_GROQ_MODEL", "llama-3.3-70b-versatile")
    payload = _http_json(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        json_body={
            "model": model,
            "temperature": 0.2,
            "max_tokens": 220,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a placement AI co-pilot. Return exactly one line in format: "
                        "REASONING || ACTION. Keep it concise, no markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout_sec=9.0,
    )
    if not payload:
        return ""
    try:
        return str(payload["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _call_gemini_reasoner(prompt: str) -> str:
    gemini_key = _resolve_secret("PLACEMENTPRO_GEMINI_API_KEY", "GEMINI_API_KEY", "GEMINI_KEY")
    if not gemini_key:
        return ""

    model = _env("PLACEMENTPRO_GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    payload = _http_json(
        "POST",
        url,
        headers={"Content-Type": "application/json"},
        json_body={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 220},
        },
        timeout_sec=9.0,
    )
    if not payload:
        return ""
    try:
        return str(payload["candidates"][0]["content"]["parts"][0]["text"]).strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _llm_reason_action(
    *,
    student: dict[str, Any],
    company: dict[str, Any],
    decision: str,
    deterministic_reasoning: str,
    deterministic_action: str,
    external_context: str,
) -> tuple[str, str]:
    if not _external_ai_enabled():
        return deterministic_reasoning, deterministic_action

    provider = _env("PLACEMENTPRO_PRIMARY_LLM", "groq").lower()
    prompt = (
        f"Student: {student['name']} | CGPA {student['cgpa']} | Backlogs {student['backlogs']} | "
        f"Deadlines missed {student['deadlines_missed']} | Skills {student['skills']} | "
        f"Verified {student['verified_skills']}.\n"
        f"Company: {company['company_name']} {company['role']} | Required {company['required_skills']} | "
        f"Decision: {decision}.\n"
        f"Deterministic reasoning: {deterministic_reasoning}\n"
        f"Deterministic action: {deterministic_action}\n"
        f"External market context: {external_context or 'none'}\n"
        "Improve reasoning and give one autonomous next action. Format exactly: REASONING || ACTION."
    )

    response = ""
    if provider == "gemini":
        response = _call_gemini_reasoner(prompt) or _call_groq_reasoner(prompt)
    else:
        response = _call_groq_reasoner(prompt) or _call_gemini_reasoner(prompt)

    if not response or "||" not in response:
        return deterministic_reasoning, deterministic_action

    reasoning_part, action_part = response.split("||", maxsplit=1)
    reasoning = reasoning_part.strip() or deterministic_reasoning
    action = action_part.strip() or deterministic_action
    return reasoning, action


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing_names = {row["name"] for row in existing}
    if column in existing_names:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    snippet = match.group(0)
    try:
        return json.loads(snippet)
    except ValueError:
        return None


def _call_groq_quiz_json(prompt: str) -> dict[str, Any] | None:
    groq_key = _resolve_secret("PLACEMENTPRO_GROQ_API_KEY", "GROQ_API_KEY", "GROK_KEY")
    if not groq_key:
        return None

    model = _env("PLACEMENTPRO_GROQ_MODEL", "llama-3.3-70b-versatile")
    payload = _http_json(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        json_body={
            "model": model,
            "temperature": 0.2,
            "max_tokens": 500,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON object only with key 'questions' containing exactly 3 objects. "
                        "Each question object must include: question, difficulty, expected_topics (array), starter_hint."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout_sec=10.0,
    )
    if not payload:
        return None
    try:
        content = str(payload["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError):
        return None
    return _extract_json_object(content)


def _call_gemini_quiz_json(prompt: str) -> dict[str, Any] | None:
    gemini_key = _resolve_secret("PLACEMENTPRO_GEMINI_API_KEY", "GEMINI_API_KEY", "GEMINI_KEY")
    if not gemini_key:
        return None

    model = _env("PLACEMENTPRO_GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    payload = _http_json(
        "POST",
        url,
        headers={"Content-Type": "application/json"},
        json_body={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
        },
        timeout_sec=10.0,
    )
    if not payload:
        return None
    try:
        text = str(payload["candidates"][0]["content"]["parts"][0]["text"]).strip()
    except (KeyError, IndexError, TypeError):
        return None
    return _extract_json_object(text)


def _fallback_python_quiz(company_name: str, role: str, missing_topics: list[str]) -> list[dict[str, Any]]:
    topic_hint = ", ".join(missing_topics[:3]) if missing_topics else "core Python problem solving"
    return [
        {
            "question": (
                f"[{company_name} {role}] Given a list of transactions, write a function to "
                "group anomalies by account id and return top 3 high-risk accounts."
            ),
            "difficulty": "Medium",
            "expected_topics": ["Python dictionaries", "sorting", "data processing"],
            "starter_hint": "Use defaultdict and a custom sort key on aggregated risk scores.",
        },
        {
            "question": (
                f"Design an efficient Python function to detect the first non-repeating event id "
                f"in a stream. Optimize for O(n). Context: improve skills in {topic_hint}."
            ),
            "difficulty": "Easy-Medium",
            "expected_topics": ["hash map", "queues", "time complexity"],
            "starter_hint": "Track frequencies in a dict and maintain order with deque.",
        },
        {
            "question": (
                "Implement a mini API rate-limiter in Python for 1-minute windows and "
                "return whether each request should be allowed."
            ),
            "difficulty": "Medium-Hard",
            "expected_topics": ["sliding window", "deque", "class design"],
            "starter_hint": "Store timestamps per user and evict older-than-window entries.",
        },
    ]


def _normalize_quiz_questions(raw: dict[str, Any] | None, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw:
        return fallback
    questions = raw.get("questions")
    if not isinstance(questions, list):
        return fallback

    normalized: list[dict[str, Any]] = []
    for item in questions[:3]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        difficulty = str(item.get("difficulty", "Medium")).strip()
        expected_topics_raw = item.get("expected_topics", [])
        expected_topics = [str(topic).strip() for topic in expected_topics_raw if str(topic).strip()]
        starter_hint = str(item.get("starter_hint", "")).strip()
        if question and starter_hint:
            normalized.append(
                {
                    "question": question,
                    "difficulty": difficulty or "Medium",
                    "expected_topics": expected_topics or ["Python"],
                    "starter_hint": starter_hint,
                }
            )
    if len(normalized) == 3:
        return normalized
    return fallback


def _generate_python_quiz(
    *,
    student: dict[str, Any],
    company: dict[str, Any],
    missing_topics: list[str],
    external_context: str,
) -> list[dict[str, Any]]:
    fallback = _fallback_python_quiz(company["company_name"], company["role"], missing_topics)
    if not _external_ai_enabled():
        return fallback

    prompt = (
        f"Generate a custom 3-question Python coding quiz for student {student['name']} "
        f"applying to {company['company_name']} ({company['role']}). "
        f"Student missing topics: {missing_topics or ['Python basics']}. "
        f"Student current skills: {student['skills']}. "
        f"External context: {external_context or 'none'}. "
        "Return JSON with key questions only."
    )
    provider = _env("PLACEMENTPRO_PRIMARY_LLM", "groq").lower()
    raw = _call_gemini_quiz_json(prompt) if provider == "gemini" else _call_groq_quiz_json(prompt)
    if raw is None:
        raw = _call_groq_quiz_json(prompt) or _call_gemini_quiz_json(prompt)
    return _normalize_quiz_questions(raw, fallback)


def _send_email_dispatch(to_email: str, subject: str, html_content: str) -> tuple[str, str]:
    resend_key = _resolve_secret("PLACEMENTPRO_RESEND_API_KEY", "RESEND_API_KEY", "RESEND_KEY")
    sendgrid_key = _resolve_secret("PLACEMENTPRO_SENDGRID_API_KEY", "SENDGRID_API_KEY", "SG_API_KEY")
    from_email = _env("PLACEMENTPRO_EMAIL_FROM", "placements-bot@example.com")

    if to_email and resend_key:
        payload = _http_json(
            "POST",
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            json_body={
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            },
            timeout_sec=10.0,
        )
        if payload is not None:
            return "SENT", "resend"

    if to_email and sendgrid_key:
        payload = _http_json(
            "POST",
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"},
            json_body={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}],
            },
            timeout_sec=10.0,
        )
        if payload is not None:
            return "SENT", "sendgrid"

    return "SIMULATED", "none"


def initialize_engine() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                section TEXT NOT NULL,
                cgpa REAL NOT NULL,
                backlogs INTEGER NOT NULL DEFAULT 0,
                skills TEXT NOT NULL,
                verified_skills TEXT NOT NULL,
                resume_uploads INTEGER NOT NULL DEFAULT 0,
                mock_score INTEGER NOT NULL DEFAULT 0,
                interview_score INTEGER NOT NULL DEFAULT 0,
                deadlines_missed INTEGER NOT NULL DEFAULT 0,
                accepted_offer TEXT,
                offer_status TEXT NOT NULL DEFAULT 'NONE',
                readiness_score INTEGER NOT NULL DEFAULT 0,
                readiness_status TEXT NOT NULL DEFAULT 'UNPREPARED'
            );

            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                min_cgpa REAL NOT NULL,
                max_backlogs INTEGER NOT NULL DEFAULT 0,
                one_job_policy INTEGER NOT NULL DEFAULT 1,
                required_skills TEXT NOT NULL,
                deadline TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                match_score INTEGER NOT NULL,
                selection_probability INTEGER NOT NULL,
                risk_tag TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                autonomous_action TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(student_id, company_id),
                FOREIGN KEY(student_id) REFERENCES students(id),
                FOREIGN KEY(company_id) REFERENCES companies(id)
            );

            CREATE TABLE IF NOT EXISTS journey_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                event_time TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                intervention_type TEXT NOT NULL,
                details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_group TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS autonomous_quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                student_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                questions TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ASSIGNED',
                delivery_status TEXT NOT NULL DEFAULT 'PENDING',
                email_provider TEXT NOT NULL DEFAULT 'none',
                delivery_target TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id),
                FOREIGN KEY(company_id) REFERENCES companies(id)
            );
            """
        )

        _ensure_column(conn, "students", "email", "TEXT")

        student_count = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]
        if student_count == 0:
            _seed_initial_data(conn)
        _ensure_seed_consistency(conn)


def _seed_initial_data(conn: sqlite3.Connection) -> None:
    students = [
        {
            "id": 1,
            "name": "Umanshu Manan",
            "email": "umanshu.manan@college.edu",
            "section": "CSE-A",
            "cgpa": 8.4,
            "backlogs": 0,
            "skills": ["Python", "FastAPI", "SQL", "React"],
            "verified_skills": ["Python", "FastAPI"],
            "resume_uploads": 3,
            "mock_score": 86,
            "interview_score": 84,
            "deadlines_missed": 0,
            "accepted_offer": None,
            "offer_status": "NONE",
        },
        {
            "id": 2,
            "name": "Aman S.",
            "email": "aman.s@college.edu",
            "section": "CSE-A",
            "cgpa": 8.8,
            "backlogs": 0,
            "skills": ["Python", "React", "System Design", "FastAPI", "AI/ML"],
            "verified_skills": ["React", "Python", "FastAPI"],
            "resume_uploads": 4,
            "mock_score": 95,
            "interview_score": 91,
            "deadlines_missed": 1,
            "accepted_offer": "TCS (Accepted)",
            "offer_status": "ACCEPTED",
        },
        {
            "id": 3,
            "name": "Rahul M.",
            "email": "rahul.m@college.edu",
            "section": "CSE-B",
            "cgpa": 8.1,
            "backlogs": 0,
            "skills": ["Python", "Django", "SQL", "Communication"],
            "verified_skills": ["Python"],
            "resume_uploads": 2,
            "mock_score": 82,
            "interview_score": 74,
            "deadlines_missed": 2,
            "accepted_offer": None,
            "offer_status": "NONE",
        },
        {
            "id": 4,
            "name": "Priya K.",
            "email": "priya.k@college.edu",
            "section": "CSE-C",
            "cgpa": 7.3,
            "backlogs": 1,
            "skills": ["Java", "SQL", "Communication"],
            "verified_skills": ["SQL"],
            "resume_uploads": 1,
            "mock_score": 41,
            "interview_score": 45,
            "deadlines_missed": 3,
            "accepted_offer": None,
            "offer_status": "NONE",
        },
        {
            "id": 5,
            "name": "Neha R.",
            "email": "neha.r@college.edu",
            "section": "ECE-A",
            "cgpa": 6.6,
            "backlogs": 2,
            "skills": ["C", "Communication"],
            "verified_skills": [],
            "resume_uploads": 1,
            "mock_score": 28,
            "interview_score": 32,
            "deadlines_missed": 4,
            "accepted_offer": None,
            "offer_status": "NONE",
        },
    ]

    companies = [
        {
            "id": 1,
            "company_name": "Intuit",
            "role": "SDE - Backend",
            "min_cgpa": 7.5,
            "max_backlogs": 0,
            "one_job_policy": 1,
            "required_skills": ["Python", "FastAPI", "AI/ML", "SQL"],
            "deadline": "2026-04-12",
        },
        {
            "id": 2,
            "company_name": "Amazon",
            "role": "Frontend Engineer",
            "min_cgpa": 8.0,
            "max_backlogs": 0,
            "one_job_policy": 1,
            "required_skills": ["React", "JavaScript", "System Design"],
            "deadline": "2026-04-14",
        },
        {
            "id": 3,
            "company_name": "Microsoft",
            "role": "Cloud Support Engineer",
            "min_cgpa": 7.0,
            "max_backlogs": 1,
            "one_job_policy": 1,
            "required_skills": ["Azure", "Communication", "SQL"],
            "deadline": "2026-04-15",
        },
        {
            "id": 4,
            "company_name": "Infosys",
            "role": "Associate Engineer",
            "min_cgpa": 6.5,
            "max_backlogs": 2,
            "one_job_policy": 0,
            "required_skills": ["Communication", "SQL", "Problem Solving"],
            "deadline": "2026-04-20",
        },
    ]

    now = _now_iso()
    events = [
        (1, "resume_uploaded", {"version": "v3", "focus": "backend"}, now),
        (1, "mock_interview_score", {"score": 86, "topic": "REST APIs"}, now),
        (2, "offer_received", {"company": "TCS", "status": "accepted"}, now),
        (3, "mock_interview_score", {"score": 82, "topic": "Python"}, now),
        (4, "deadline_missed", {"count": 3, "latest_company": "Amazon"}, now),
        (5, "deadline_missed", {"count": 4, "latest_company": "Intuit"}, now),
    ]

    conn.executemany(
        """
        INSERT INTO students (
            id, name, email, section, cgpa, backlogs, skills, verified_skills,
            resume_uploads, mock_score, interview_score, deadlines_missed,
            accepted_offer, offer_status
        ) VALUES (
            :id, :name, :email, :section, :cgpa, :backlogs, :skills, :verified_skills,
            :resume_uploads, :mock_score, :interview_score, :deadlines_missed,
            :accepted_offer, :offer_status
        )
        """,
        [
            {
                **student,
                "skills": _to_json(student["skills"]),
                "verified_skills": _to_json(student["verified_skills"]),
            }
            for student in students
        ],
    )

    conn.executemany(
        """
        INSERT INTO companies (
            id, company_name, role, min_cgpa, max_backlogs, one_job_policy, required_skills, deadline
        ) VALUES (
            :id, :company_name, :role, :min_cgpa, :max_backlogs, :one_job_policy, :required_skills, :deadline
        )
        """,
        [{**company, "required_skills": _to_json(company["required_skills"])} for company in companies],
    )

    conn.executemany(
        """
        INSERT INTO journey_events (student_id, event_type, payload, event_time)
        VALUES (?, ?, ?, ?)
        """,
        [(student_id, event_type, _to_json(payload), event_time) for student_id, event_type, payload, event_time in events],
    )


def _ensure_seed_consistency(conn: sqlite3.Connection) -> None:
    """Keeps demo dataset aligned with PS1 showcase behaviors on existing DBs."""
    row = conn.execute("SELECT skills FROM students WHERE id = 1").fetchone()
    if row is None:
        return

    skills = _from_json(row["skills"], [])
    if "AI/ML" not in skills:
        skills.append("AI/ML")
        conn.execute("UPDATE students SET skills = ? WHERE id = 1", (_to_json(skills),))

    email_map = {
        1: "umanshu.manan@college.edu",
        2: "aman.s@college.edu",
        3: "rahul.m@college.edu",
        4: "priya.k@college.edu",
        5: "neha.r@college.edu",
    }
    for student_id, email in email_map.items():
        conn.execute(
            "UPDATE students SET email = COALESCE(email, ?) WHERE id = ?",
            (email, student_id),
        )

    extra_students = [
        {
            "id": 6,
            "name": "Karthik V.",
            "email": "karthik.v@college.edu",
            "section": "CSE-D",
            "cgpa": 9.1,
            "backlogs": 0,
            "skills": ["Python", "FastAPI", "AI/ML", "SQL", "Docker"],
            "verified_skills": ["Python", "AI/ML", "FastAPI"],
            "resume_uploads": 5,
            "mock_score": 93,
            "interview_score": 89,
            "deadlines_missed": 0,
            "accepted_offer": None,
            "offer_status": "NONE",
        },
        {
            "id": 7,
            "name": "Sana F.",
            "email": "sana.f@college.edu",
            "section": "IT-B",
            "cgpa": 7.8,
            "backlogs": 0,
            "skills": ["React", "JavaScript", "Node.js", "Communication"],
            "verified_skills": ["React"],
            "resume_uploads": 2,
            "mock_score": 68,
            "interview_score": 63,
            "deadlines_missed": 1,
            "accepted_offer": None,
            "offer_status": "NONE",
        },
        {
            "id": 8,
            "name": "Yash P.",
            "email": "yash.p@college.edu",
            "section": "ECE-B",
            "cgpa": 6.9,
            "backlogs": 2,
            "skills": ["C", "Embedded Systems", "Communication"],
            "verified_skills": [],
            "resume_uploads": 1,
            "mock_score": 39,
            "interview_score": 44,
            "deadlines_missed": 2,
            "accepted_offer": None,
            "offer_status": "NONE",
        },
    ]
    for student in extra_students:
        exists = conn.execute("SELECT id FROM students WHERE id = ?", (student["id"],)).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO students (
                id, name, email, section, cgpa, backlogs, skills, verified_skills, resume_uploads,
                mock_score, interview_score, deadlines_missed, accepted_offer, offer_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student["id"],
                student["name"],
                student["email"],
                student["section"],
                student["cgpa"],
                student["backlogs"],
                _to_json(student["skills"]),
                _to_json(student["verified_skills"]),
                student["resume_uploads"],
                student["mock_score"],
                student["interview_score"],
                student["deadlines_missed"],
                student["accepted_offer"],
                student["offer_status"],
            ),
        )
        _append_journey_event(
            conn,
            student_id=student["id"],
            event_type="profile_seeded",
            payload={"source": "consistency_patch"},
        )

    extra_companies = [
        {
            "id": 5,
            "company_name": "Atlassian",
            "role": "SDE 1",
            "min_cgpa": 8.2,
            "max_backlogs": 0,
            "one_job_policy": 1,
            "required_skills": ["Python", "System Design", "SQL", "Docker"],
            "deadline": "2026-04-22",
        },
        {
            "id": 6,
            "company_name": "NVIDIA",
            "role": "AI Infrastructure Intern",
            "min_cgpa": 8.5,
            "max_backlogs": 0,
            "one_job_policy": 1,
            "required_skills": ["Python", "AI/ML", "Linux", "CUDA"],
            "deadline": "2026-04-24",
        },
    ]
    for company in extra_companies:
        exists = conn.execute("SELECT id FROM companies WHERE id = ?", (company["id"],)).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO companies (
                id, company_name, role, min_cgpa, max_backlogs, one_job_policy, required_skills, deadline, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                company["id"],
                company["company_name"],
                company["role"],
                company["min_cgpa"],
                company["max_backlogs"],
                company["one_job_policy"],
                _to_json(company["required_skills"]),
                company["deadline"],
            ),
        )

def _fetch_students(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM students ORDER BY id").fetchall()
    students: list[dict[str, Any]] = []
    for row in rows:
        students.append(
            {
                **dict(row),
                "skills": _from_json(row["skills"], []),
                "verified_skills": _from_json(row["verified_skills"], []),
            }
        )
    return students


def _fetch_companies(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM companies WHERE active = 1 ORDER BY id").fetchall()
    companies: list[dict[str, Any]] = []
    for row in rows:
        companies.append({**dict(row), "required_skills": _from_json(row["required_skills"], [])})
    return companies


def _build_profile_snapshot(student_row: sqlite3.Row) -> StudentProfileSnapshot:
    return StudentProfileSnapshot(
        id=student_row["id"],
        name=student_row["name"],
        section=student_row["section"],
        cgpa=float(student_row["cgpa"]),
        backlogs=int(student_row["backlogs"]),
        skills=_from_json(student_row["skills"], []),
        verified_skills=_from_json(student_row["verified_skills"], []),
        readiness_score=int(student_row["readiness_score"]),
        readiness_status=student_row["readiness_status"],
        accepted_offer=student_row["accepted_offer"],
        deadlines_missed=int(student_row["deadlines_missed"]),
    )


def _build_profile_snapshot_from_student(student: dict[str, Any]) -> StudentProfileSnapshot:
    _, readiness_score, readiness_status = _predictive_agent(student, 50)
    return StudentProfileSnapshot(
        id=int(student["id"]),
        name=str(student["name"]),
        section=str(student["section"]),
        cgpa=float(student["cgpa"]),
        backlogs=int(student["backlogs"]),
        skills=list(student["skills"]),
        verified_skills=list(student["verified_skills"]),
        readiness_score=int(readiness_score),
        readiness_status=readiness_status,
        accepted_offer=student.get("accepted_offer"),
        deadlines_missed=int(student["deadlines_missed"]),
    )


def _decide_application_status(*, eligible: bool, match_score: int, selection_probability: int) -> str:
    if not eligible:
        return "BLOCKED"
    decision = "RECOMMENDED" if match_score >= 90 else "OPEN"
    if selection_probability < 30:
        decision = "AT_RISK"
    return decision


def _deadline_tradeoff_penalty(prompt: str, company_name: str, deadline: str) -> tuple[int, str]:
    normalized = prompt.lower()
    penalty = 0
    reasons: list[str] = []

    if re.search(r"miss(?:ed|ing)?\s+\d*\s*deadlines?", normalized) or (
        "miss" in normalized and "deadline" in normalized
    ):
        penalty += 18
        reasons.append("deadline miss intent detected")

    if "this weekend" in normalized or "weekend" in normalized:
        try:
            deadline_date = datetime.fromisoformat(deadline).date()
            today = datetime.now(timezone.utc).date()
            days_to_deadline = (deadline_date - today).days
        except ValueError:
            days_to_deadline = None

        if days_to_deadline is not None and 0 <= days_to_deadline <= 3:
            penalty += 10
            reasons.append("weekend focus may reduce near-deadline availability")

    if company_name.lower() in normalized and "deadline" in normalized and ("miss" in normalized or "delay" in normalized):
        penalty += 6
        reasons.append(f"{company_name} explicitly referenced with deadline risk")

    if penalty <= 0:
        return 0, ""
    return min(30, penalty), "; ".join(reasons)


def _apply_what_if_prompt(
    student: dict[str, Any],
    prompt: str,
    companies: list[dict[str, Any]],
) -> tuple[dict[str, Any], WhatIfProfileDelta]:
    simulated = {
        **student,
        "skills": list(student["skills"]),
        "verified_skills": list(student["verified_skills"]),
    }
    delta = WhatIfProfileDelta()
    normalized = prompt.lower()

    def add_skill(skill: str, *, verify: bool = False) -> None:
        if skill not in simulated["skills"]:
            simulated["skills"].append(skill)
            if skill not in delta.skills_added:
                delta.skills_added.append(skill)
        if verify and skill not in simulated["verified_skills"]:
            simulated["verified_skills"].append(skill)
            if skill not in delta.verified_skills_added:
                delta.verified_skills_added.append(skill)

    skill_aliases = {
        "python": "Python",
        "fastapi": "FastAPI",
        "react": "React",
        "javascript": "JavaScript",
        "node.js": "Node.js",
        "nodejs": "Node.js",
        "sql": "SQL",
        "system design": "System Design",
        "communication": "Communication",
        "aws": "AWS",
        "azure": "Azure",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "linux": "Linux",
        "cuda": "CUDA",
        "ai/ml": "AI/ML",
        "aiml": "AI/ML",
        "ml": "AI/ML",
        "django": "Django",
    }

    learning_cues = ("learn", "upskill", "master", "add", "study", "improve", "practice")
    if any(cue in normalized for cue in learning_cues):
        for token, canonical in skill_aliases.items():
            if token in normalized:
                add_skill(canonical)

    if "aws" in normalized:
        requires_azure = any("Azure" in company["required_skills"] for company in companies)
        has_azure = "Azure" in simulated["skills"] or "Azure" in simulated["verified_skills"]
        if requires_azure and not has_azure:
            add_skill("Azure")
            delta.assumptions.append(
                "Mapped AWS upskilling to partial Azure readiness for cloud-role transferability."
            )

    verify_cues = ("verify", "verified", "certified", "certification")
    if any(cue in normalized for cue in verify_cues):
        for skill in list(delta.skills_added):
            add_skill(skill, verify=True)

    clear_backlog_phrases = ("clear backlog", "clear backlogs", "clear my backlog", "no backlog", "zero backlog")
    if any(phrase in normalized for phrase in clear_backlog_phrases) or re.search(r"clear\s+\w+\s+backlogs?", normalized):
        old_backlogs = int(simulated["backlogs"])
        simulated["backlogs"] = 0
        delta.backlogs_delta += 0 - old_backlogs
    else:
        backlog_to_match = re.search(r"(?:backlogs?|arrears?)\s*(?:to|=)?\s*(\d+)", normalized)
        if backlog_to_match:
            target_backlogs = max(0, int(backlog_to_match.group(1)))
            old_backlogs = int(simulated["backlogs"])
            simulated["backlogs"] = target_backlogs
            delta.backlogs_delta += target_backlogs - old_backlogs

    miss_deadlines_match = re.search(r"miss(?:ed|ing)?\s+(\d+)\s+deadlines?", normalized)
    if miss_deadlines_match:
        miss_count = max(1, int(miss_deadlines_match.group(1)))
        simulated["deadlines_missed"] = int(simulated["deadlines_missed"]) + miss_count
        delta.deadlines_missed_delta += miss_count
    elif "miss deadline" in normalized or "miss deadlines" in normalized:
        simulated["deadlines_missed"] = int(simulated["deadlines_missed"]) + 1
        delta.deadlines_missed_delta += 1

    no_miss_deadline_phrases = ("no missed deadline", "never miss deadline", "never miss deadlines")
    if any(phrase in normalized for phrase in no_miss_deadline_phrases):
        old_missed = int(simulated["deadlines_missed"])
        simulated["deadlines_missed"] = 0
        delta.deadlines_missed_delta += 0 - old_missed

    mock_to_match = re.search(r"mock(?:\s+interview)?(?:\s+score)?\s*(?:to|=)?\s*(\d{1,3})", normalized)
    if mock_to_match:
        target_score = max(0, min(100, int(mock_to_match.group(1))))
        old_score = int(simulated["mock_score"])
        simulated["mock_score"] = target_score
        delta.mock_score_delta += target_score - old_score
    else:
        mock_by_match = re.search(r"mock(?:\s+interview)?\s*(?:by|improve by)\s*(\d{1,2})", normalized)
        if mock_by_match:
            bump = max(1, int(mock_by_match.group(1)))
            old_score = int(simulated["mock_score"])
            simulated["mock_score"] = max(0, min(100, old_score + bump))
            delta.mock_score_delta += int(simulated["mock_score"]) - old_score

    interview_to_match = re.search(r"interview(?:\s+score)?\s*(?:to|=)?\s*(\d{1,3})", normalized)
    if interview_to_match:
        target_score = max(0, min(100, int(interview_to_match.group(1))))
        old_score = int(simulated["interview_score"])
        simulated["interview_score"] = target_score
        delta.interview_score_delta += target_score - old_score

    if "drop offer" in normalized or "clear offer" in normalized or "reject offer" in normalized:
        if simulated.get("accepted_offer"):
            simulated["accepted_offer"] = None
            simulated["offer_status"] = "NONE"
            delta.accepted_offer_cleared = True

    if "this weekend" in normalized or "weekend" in normalized:
        delta.assumptions.append("Applied near-deadline weekend trade-off heuristic during simulation.")

    touched = (
        delta.skills_added
        or delta.verified_skills_added
        or delta.backlogs_delta
        or delta.deadlines_missed_delta
        or delta.mock_score_delta
        or delta.interview_score_delta
        or delta.accepted_offer_cleared
    )
    if not touched:
        delta.assumptions.append("No explicit profile edits parsed; scenario ran on current profile.")

    return simulated, delta


def _evaluate_company_for_student(
    *,
    student: dict[str, Any],
    company: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    match_score, match_reasoning = _matching_agent(student, company)
    selection_probability, _, readiness_status = _predictive_agent(student, match_score)
    eligible, policy_reasons = _policy_and_eligibility_agent(student, company)

    penalty, penalty_reason = _deadline_tradeoff_penalty(prompt, company["company_name"], company["deadline"])
    adjusted_probability = selection_probability
    if eligible and penalty > 0:
        adjusted_probability = max(1, selection_probability - penalty)

    decision = _decide_application_status(
        eligible=eligible,
        match_score=match_score,
        selection_probability=adjusted_probability,
    )
    policy_reasoning = "Eligible." if eligible else " ".join(policy_reasons)
    deadline_note = f" Deadline pressure penalty: -{penalty}% ({penalty_reason})." if penalty > 0 else ""
    reasoning = (
        f"Matching Agent: {match_reasoning} "
        f"Predictive Agent: readiness {readiness_status}, selection {adjusted_probability}%. "
        f"Policy Agent: {policy_reasoning}.{deadline_note}"
    )
    return {
        "match_score": int(match_score),
        "selection_probability": int(adjusted_probability),
        "decision": decision,
        "reasoning": reasoning,
    }


def _build_autonomous_quiz_model(row: sqlite3.Row) -> AutonomousQuiz:
    questions_raw = _from_json(row["questions"], [])
    questions = [
        QuizQuestion(
            question=str(item.get("question", "")),
            difficulty=str(item.get("difficulty", "Medium")),
            expected_topics=[str(topic) for topic in item.get("expected_topics", [])],
            starter_hint=str(item.get("starter_hint", "")),
        )
        for item in questions_raw
        if isinstance(item, dict)
    ]
    return AutonomousQuiz(
        quiz_id=int(row["id"]),
        token=row["token"],
        company=row["company_name"],
        role=row["role"],
        topic=row["topic"],
        delivery_status=row["delivery_status"],
        created_at=row["created_at"],
        questions=questions,
    )


def _create_autonomous_python_quiz_if_needed(
    conn: sqlite3.Connection,
    *,
    student: dict[str, Any],
    company: dict[str, Any],
    missing_topics: list[str],
    external_context: str,
) -> str:
    existing = conn.execute(
        """
        SELECT id, token
        FROM autonomous_quizzes
        WHERE student_id = ? AND company_id = ? AND topic = 'PYTHON_UPSKILL'
          AND status IN ('ASSIGNED', 'SENT', 'OPENED')
        ORDER BY id DESC
        LIMIT 1
        """,
        (student["id"], company["id"]),
    ).fetchone()
    frontend_base = _env("PLACEMENTPRO_FRONTEND_BASE_URL", "http://localhost:5173")
    if existing:
        return f"Autonomous quiz already active: {frontend_base.rstrip('/')}/quiz/{existing['token']}"

    questions = _generate_python_quiz(
        student=student,
        company=company,
        missing_topics=missing_topics,
        external_context=external_context,
    )
    token = secrets.token_urlsafe(12)
    quiz_link = f"{frontend_base.rstrip('/')}/quiz/{token}"
    subject = f"PlacementPro Autonomous Upskiller: {company['company_name']} Python Quiz"
    html_body = (
        f"<p>Hello {student['name']},</p>"
        f"<p>Your profile was flagged as at-risk for <b>{company['company_name']} - {company['role']}</b> "
        "due to Python readiness gaps. An autonomous 3-question upskilling quiz has been generated.</p>"
        f"<p><a href='{quiz_link}'>Open your quiz now</a></p>"
        "<p>Complete it to unlock improved recommendation chances.</p>"
    )
    delivery_status, provider = _send_email_dispatch(student.get("email", ""), subject, html_body)

    now = _now_iso()
    conn.execute(
        """
        INSERT INTO autonomous_quizzes (
            token, student_id, company_id, topic, questions, status, delivery_status,
            email_provider, delivery_target, created_at, updated_at
        ) VALUES (?, ?, ?, 'PYTHON_UPSKILL', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            token,
            student["id"],
            company["id"],
            _to_json(questions),
            "SENT" if delivery_status == "SENT" else "ASSIGNED",
            delivery_status,
            provider,
            student.get("email", ""),
            now,
            now,
        ),
    )

    _create_intervention_if_needed(
        conn,
        student_id=student["id"],
        intervention_type="AUTONOMOUS_UPSKILLER_QUIZ",
        details=f"Python quiz generated for {company['company_name']}: {quiz_link}",
    )
    _create_communication_if_needed(
        conn,
        target_group=f"STUDENT:{student['id']}",
        message=(
            f"Autonomous Upskiller dispatched ({delivery_status}) via {provider}: "
            f"{company['company_name']} Python quiz link {quiz_link}"
        ),
    )
    _append_journey_event(
        conn,
        student_id=student["id"],
        event_type="autonomous_quiz_generated",
        payload={
            "company": company["company_name"],
            "topic": "PYTHON_UPSKILL",
            "delivery_status": delivery_status,
            "provider": provider,
            "quiz_link": quiz_link,
        },
    )
    return f"Autonomous upskilling quiz dispatched ({delivery_status}) via {provider}: {quiz_link}"


def _matching_agent(student: dict[str, Any], company: dict[str, Any]) -> tuple[int, str]:
    student_skill_set = {skill.lower() for skill in student["skills"] + student["verified_skills"]}
    required_skills = company["required_skills"]
    required_skill_set = {skill.lower() for skill in required_skills}

    if not required_skill_set:
        return 0, "No required skills configured for this company."

    matched = [skill for skill in required_skills if skill.lower() in student_skill_set]
    missing = [skill for skill in required_skills if skill.lower() not in student_skill_set]

    match_score = int(round((len(matched) / len(required_skill_set)) * 100))
    reasoning = (
        f"Matched {len(matched)}/{len(required_skills)} required skills "
        f"({', '.join(matched) if matched else 'none'}). "
        f"Missing: {', '.join(missing) if missing else 'none'}."
    )
    return match_score, reasoning


def _predictive_agent(student: dict[str, Any], match_score: int) -> tuple[int, int, str]:
    cgpa_component = (student["cgpa"] / 10.0) * 40
    mock_component = (student["mock_score"] / 100.0) * 30
    interview_component = (student["interview_score"] / 100.0) * 30

    penalty = (student["backlogs"] * 6) + (student["deadlines_missed"] * 7)
    readiness_score = int(round(max(0, min(100, cgpa_component + mock_component + interview_component - penalty))))

    probability_raw = readiness_score * 0.7 + (match_score * 0.3)
    selection_probability = int(round(max(1, min(99, probability_raw))))

    if readiness_score >= 75:
        readiness_status = "READY"
    elif readiness_score >= 45:
        readiness_status = "RISKY"
    else:
        readiness_status = "UNPREPARED"

    return selection_probability, readiness_score, readiness_status


def _policy_and_eligibility_agent(student: dict[str, Any], company: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if student["cgpa"] < company["min_cgpa"]:
        reasons.append(f"CGPA {student['cgpa']} is below required {company['min_cgpa']}.")

    if student["backlogs"] > company["max_backlogs"]:
        reasons.append(
            f"Backlogs {student['backlogs']} exceed allowed {company['max_backlogs']} for {company['company_name']}."
        )

    if company["one_job_policy"] == 1 and student["accepted_offer"]:
        reasons.append(
            f"One-job policy active and student already accepted {student['accepted_offer']}."
        )

    if student["deadlines_missed"] >= 5:
        reasons.append("Repeated deadline misses triggered temporary application lock.")

    return len(reasons) == 0, reasons


def _upsert_application(
    conn: sqlite3.Connection,
    *,
    student_id: int,
    company_id: int,
    status: str,
    match_score: int,
    selection_probability: int,
    risk_tag: str,
    reasoning: str,
    autonomous_action: str,
) -> None:
    conn.execute(
        """
        INSERT INTO applications (
            student_id, company_id, status, match_score, selection_probability,
            risk_tag, reasoning, autonomous_action, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, company_id) DO UPDATE SET
            status = excluded.status,
            match_score = excluded.match_score,
            selection_probability = excluded.selection_probability,
            risk_tag = excluded.risk_tag,
            reasoning = excluded.reasoning,
            autonomous_action = excluded.autonomous_action,
            updated_at = excluded.updated_at
        """,
        (
            student_id,
            company_id,
            status,
            match_score,
            selection_probability,
            risk_tag,
            reasoning,
            autonomous_action,
            _now_iso(),
        ),
    )


def _create_intervention_if_needed(
    conn: sqlite3.Connection,
    *,
    student_id: int,
    intervention_type: str,
    details: str,
    status: str = "PENDING",
) -> bool:
    exists = conn.execute(
        """
        SELECT id FROM interventions
        WHERE student_id = ? AND intervention_type = ? AND details = ? AND status = ?
        LIMIT 1
        """,
        (student_id, intervention_type, details, status),
    ).fetchone()
    if exists:
        return False

    conn.execute(
        """
        INSERT INTO interventions (student_id, intervention_type, details, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, intervention_type, details, status, _now_iso()),
    )
    return True


def _create_communication_if_needed(conn: sqlite3.Connection, *, target_group: str, message: str) -> bool:
    existing = conn.execute(
        """
        SELECT id FROM communications
        WHERE target_group = ? AND message = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (target_group, message),
    ).fetchone()
    if existing:
        return False

    conn.execute(
        """
        INSERT INTO communications (target_group, message, created_at)
        VALUES (?, ?, ?)
        """,
        (target_group, message, _now_iso()),
    )
    return True


def _append_journey_event(conn: sqlite3.Connection, *, student_id: int, event_type: str, payload: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO journey_events (student_id, event_type, payload, event_time)
        VALUES (?, ?, ?, ?)
        """,
        (student_id, event_type, _to_json(payload), _now_iso()),
    )


def _build_flight_risk_alerts(conn: sqlite3.Connection) -> list[FlightRiskAlert]:
    students = _fetch_students(conn)
    alerts: list[FlightRiskAlert] = []

    for student in students:
        if not student["accepted_offer"]:
            continue

        best_alt = conn.execute(
            """
            SELECT a.*, c.company_name
            FROM applications a
            JOIN companies c ON c.id = a.company_id
            WHERE a.student_id = ?
              AND c.company_name NOT LIKE ?
            ORDER BY a.match_score DESC, a.selection_probability DESC
            LIMIT 1
            """,
            (student["id"], f"%{student['accepted_offer'].split('(')[0].strip()}%"),
        ).fetchone()

        if not best_alt:
            continue

        risk_percent = min(99, 65 + max(0, best_alt["match_score"] - 75) * 2 + (student["mock_score"] // 8))
        if risk_percent < 70:
            continue

        waitlist_candidate_row = conn.execute(
            """
            SELECT s.name
            FROM applications a
            JOIN students s ON s.id = a.student_id
            WHERE a.company_id = ?
              AND a.student_id <> ?
              AND a.status IN ('RECOMMENDED', 'OPEN')
            ORDER BY a.selection_probability DESC, a.match_score DESC
            LIMIT 1
            """,
            (best_alt["company_id"], student["id"]),
        ).fetchone()

        candidate_name = waitlist_candidate_row["name"] if waitlist_candidate_row else "No immediate candidate"
        risk_label = "CRITICAL" if risk_percent >= 85 else "HIGH"
        reasoning = (
            f"Accepted offer is {student['accepted_offer']} but {best_alt['company_name']} "
            f"match is {best_alt['match_score']}% with selection probability {best_alt['selection_probability']}%."
        )
        action = (
            f"Agent pre-screened waitlist candidate: {candidate_name} for potential replacement "
            f"if {student['name']} drops the offer."
        )

        _create_intervention_if_needed(
            conn,
            student_id=student["id"],
            intervention_type="WAITLIST_AUTOMATION",
            details=action,
        )

        _create_communication_if_needed(
            conn,
            target_group="TPC",
            message=f"Flight risk detected for {student['name']} ({risk_label} {risk_percent}%). {action}",
        )

        alerts.append(
            FlightRiskAlert(
                student_name=student["name"],
                current_offer=student["accepted_offer"],
                risk_level=f"{risk_label} ({risk_percent}%)",
                agent_reasoning=reasoning,
                autonomous_action=action,
            )
        )

    return alerts


def _run_cycle_engine(conn: sqlite3.Connection) -> tuple[DecisionCycleSummary, list[AgentDecision], list[FlightRiskAlert]]:
    students = _fetch_students(conn)
    companies = _fetch_companies(conn)
    company_context_map: dict[int, str] = {}
    if _external_ai_enabled():
        for company in companies:
            company_context_map[company["id"]] = _collect_company_external_context(
                company["company_name"],
                company["role"],
            )
    llm_budget = int(_env("PLACEMENTPRO_MAX_LLM_DECISIONS_PER_CYCLE", "12") or 12)
    llm_calls = 0

    recommendations_created = 0
    blocked_applications = 0
    mock_interviews_assigned = 0
    tpc_alerts_triggered = 0
    decisions: list[AgentDecision] = []

    for student in students:
        for company in companies:
            match_score, match_reasoning = _matching_agent(student, company)
            selection_probability, readiness_score, readiness_status = _predictive_agent(student, match_score)
            eligible, policy_reasons = _policy_and_eligibility_agent(student, company)

            conn.execute(
                """
                UPDATE students
                SET readiness_score = ?, readiness_status = ?
                WHERE id = ?
                """,
                (readiness_score, readiness_status, student["id"]),
            )

            if not eligible:
                blocked_applications += 1
                policy_reason_text = " ".join(policy_reasons)
                deterministic_reasoning = f"Policy & Eligibility Agent: {policy_reason_text}"
                deterministic_action = "Policy Agent blocked application."
                action_items = [deterministic_action]
                autonomous_upskiller_triggered = False

                required_lower = {skill.lower() for skill in company["required_skills"]}
                student_lower = {skill.lower() for skill in (student["skills"] + student["verified_skills"])}
                python_missing = "python" in required_lower and "python" not in student_lower
                blocked_only_by_one_job_policy = len(policy_reasons) == 1 and "One-job policy active" in policy_reasons[0]

                if (
                    python_missing
                    and selection_probability < 45
                    and not blocked_only_by_one_job_policy
                ):
                    missing_topics = [skill for skill in company["required_skills"] if skill.lower() not in student_lower]
                    quiz_action = _create_autonomous_python_quiz_if_needed(
                        conn,
                        student=student,
                        company=company,
                        missing_topics=missing_topics,
                        external_context=company_context_map.get(company["id"], ""),
                    )
                    action_items.append(quiz_action)
                    autonomous_upskiller_triggered = True

                deterministic_action = " ".join(action_items)
                reasoning, action = deterministic_reasoning, deterministic_action
                if llm_calls < llm_budget and not autonomous_upskiller_triggered:
                    reasoning, action = _llm_reason_action(
                        student=student,
                        company=company,
                        decision="BLOCKED",
                        deterministic_reasoning=deterministic_reasoning,
                        deterministic_action=deterministic_action,
                        external_context=company_context_map.get(company["id"], ""),
                    )
                    if reasoning != deterministic_reasoning or action != deterministic_action:
                        llm_calls += 1
                _upsert_application(
                    conn,
                    student_id=student["id"],
                    company_id=company["id"],
                    status="BLOCKED",
                    match_score=match_score,
                    selection_probability=selection_probability,
                    risk_tag=readiness_status,
                    reasoning=reasoning,
                    autonomous_action=action,
                )
                decisions.append(
                    AgentDecision(
                        student_id=student["id"],
                        company_id=company["id"],
                        decision="BLOCKED",
                        match_score=match_score,
                        selection_probability=selection_probability,
                        reasoning=reasoning,
                        autonomous_action=action,
                    )
                )
                continue

            decision = "RECOMMENDED" if match_score >= 90 else "OPEN"
            action_items: list[str] = []
            autonomous_upskiller_triggered = False

            if decision == "RECOMMENDED":
                recommendations_created += 1
                action_items.append("Student moved to recommended list.")

            if selection_probability < 30:
                detail = (
                    f"Selection probability dropped to {selection_probability}% for {company['company_name']}. "
                    "Mandatory mock interview assigned."
                )
                created = _create_intervention_if_needed(
                    conn,
                    student_id=student["id"],
                    intervention_type="MANDATORY_MOCK_INTERVIEW",
                    details=detail,
                )
                if created:
                    mock_interviews_assigned += 1
                    _append_journey_event(
                        conn,
                        student_id=student["id"],
                        event_type="mock_interview_assigned",
                        payload={"company": company["company_name"], "selection_probability": selection_probability},
                    )
                action_items.append("Mandatory mock interview assigned by Predictive Agent.")
                decision = "AT_RISK"

            if student["deadlines_missed"] >= 3:
                detail = (
                    f"Student missed {student['deadlines_missed']} deadlines and has been flagged for TPC follow-up."
                )
                created = _create_intervention_if_needed(
                    conn,
                    student_id=student["id"],
                    intervention_type="TPC_ALERT",
                    details=detail,
                )
                if created:
                    tpc_alerts_triggered += 1
                    _append_journey_event(
                        conn,
                        student_id=student["id"],
                        event_type="profile_flagged",
                        payload={"reason": "missed_three_deadlines", "count": student["deadlines_missed"]},
                    )
                _create_communication_if_needed(conn, target_group="TPC", message=detail)
                action_items.append("TPC notified due to repeated deadline misses.")

            if match_score >= 85 and selection_probability >= 70:
                _create_communication_if_needed(
                    conn,
                    target_group=f"STUDENT:{student['id']}",
                    message=(
                        f"Nudge: {company['company_name']} ({company['role']}) is a strong fit at "
                        f"{match_score}% match and {selection_probability}% predicted selection chance."
                    ),
                )

            required_lower = {skill.lower() for skill in company["required_skills"]}
            student_lower = {skill.lower() for skill in (student["skills"] + student["verified_skills"])}
            python_missing = "python" in required_lower and "python" not in student_lower
            if python_missing and (decision == "AT_RISK" or selection_probability < 45):
                missing_topics = [skill for skill in company["required_skills"] if skill.lower() not in student_lower]
                quiz_action = _create_autonomous_python_quiz_if_needed(
                    conn,
                    student=student,
                    company=company,
                    missing_topics=missing_topics,
                    external_context=company_context_map.get(company["id"], ""),
                )
                action_items.append(quiz_action)
                autonomous_upskiller_triggered = True

            deterministic_reasoning = (
                f"Matching Agent: {match_reasoning} "
                f"Predictive Agent: selection chance {selection_probability}% and readiness {readiness_status}. "
                "Policy Agent: eligible."
            )
            deterministic_action = " ".join(action_items) if action_items else "No autonomous action required."
            reasoning, action = deterministic_reasoning, deterministic_action
            if llm_calls < llm_budget and decision in {"RECOMMENDED", "AT_RISK", "OPEN"} and not autonomous_upskiller_triggered:
                reasoning, action = _llm_reason_action(
                    student=student,
                    company=company,
                    decision=decision,
                    deterministic_reasoning=deterministic_reasoning,
                    deterministic_action=deterministic_action,
                    external_context=company_context_map.get(company["id"], ""),
                )
                if reasoning != deterministic_reasoning or action != deterministic_action:
                    llm_calls += 1

            _upsert_application(
                conn,
                student_id=student["id"],
                company_id=company["id"],
                status=decision,
                match_score=match_score,
                selection_probability=selection_probability,
                risk_tag=readiness_status,
                reasoning=reasoning,
                autonomous_action=action,
            )

            decisions.append(
                AgentDecision(
                    student_id=student["id"],
                    company_id=company["id"],
                    decision=decision,
                    match_score=match_score,
                    selection_probability=selection_probability,
                    reasoning=reasoning,
                    autonomous_action=action,
                )
            )

    flight_risk_alerts = _build_flight_risk_alerts(conn)
    summary = DecisionCycleSummary(
        scanned_students=len(students),
        recommendations_created=recommendations_created,
        blocked_applications=blocked_applications,
        mock_interviews_assigned=mock_interviews_assigned,
        tpc_alerts_triggered=tpc_alerts_triggered,
        flight_risk_cases=len(flight_risk_alerts),
    )
    return summary, decisions, flight_risk_alerts


def run_agentic_cycle() -> DecisionCycleResponse:
    initialize_engine()
    with _connect() as conn:
        summary, decisions, _ = _run_cycle_engine(conn)
        return DecisionCycleResponse(status="success", summary=summary, decisions=decisions)


def get_live_insights() -> DashboardLiveInsightsResponse:
    initialize_engine()
    with _connect() as conn:
        _, _, flight_risk_alerts = _run_cycle_engine(conn)

        campaign_row = conn.execute(
            """
            SELECT
                c.company_name,
                COUNT(*) AS total_scanned,
                SUM(CASE WHEN a.status = 'BLOCKED' THEN 0 ELSE 1 END) AS eligible_unlocked,
                SUM(CASE WHEN a.status = 'BLOCKED' THEN 1 ELSE 0 END) AS ineligible_blocked
            FROM applications a
            JOIN companies c ON c.id = a.company_id
            GROUP BY c.company_name
            ORDER BY eligible_unlocked DESC, total_scanned DESC
            LIMIT 1
            """
        ).fetchone()

        if campaign_row is None:
            campaign = {
                "company": "No Active Campaign",
                "eligibility_enforced": {
                    "total_scanned": 0,
                    "eligible_unlocked": 0,
                    "ineligible_blocked": 0,
                },
            }
        else:
            campaign = {
                "company": campaign_row["company_name"],
                "eligibility_enforced": {
                    "total_scanned": int(campaign_row["total_scanned"]),
                    "eligible_unlocked": int(campaign_row["eligible_unlocked"]),
                    "ineligible_blocked": int(campaign_row["ineligible_blocked"]),
                },
            }

        comm_rows = conn.execute(
            """
            SELECT created_at, message
            FROM communications
            ORDER BY id DESC
            LIMIT 5
            """
        ).fetchall()
        communication_logs = [
            CommunicationLog(timestamp=_display_time(row["created_at"]), action=row["message"])
            for row in reversed(comm_rows)
        ]

        return DashboardLiveInsightsResponse(
            status="success",
            data={
                "active_campaigns": campaign,
                "flight_risk_alerts": flight_risk_alerts,
                "communication_logs": communication_logs,
            },
        )


def get_admin_analytics() -> AdminAnalyticsResponse:
    initialize_engine()
    with _connect() as conn:
        _, _, flight_risk_alerts = _run_cycle_engine(conn)

        distribution_row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN readiness_status = 'READY' THEN 1 ELSE 0 END) AS ready,
                SUM(CASE WHEN readiness_status = 'RISKY' THEN 1 ELSE 0 END) AS risky,
                SUM(CASE WHEN readiness_status = 'UNPREPARED' THEN 1 ELSE 0 END) AS unprepared
            FROM students
            """
        ).fetchone()

        intervention_count = conn.execute("SELECT COUNT(*) AS count FROM interventions").fetchone()["count"]
        communication_count = conn.execute("SELECT COUNT(*) AS count FROM communications").fetchone()["count"]
        total_students = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]
        total_companies = conn.execute("SELECT COUNT(*) AS count FROM companies WHERE active = 1").fetchone()["count"]
        status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM applications
            GROUP BY status
            """
        ).fetchall()
        status_snapshot = {row["status"]: int(row["count"]) for row in status_rows}

        at_risk_rows = conn.execute(
            """
            SELECT id, name, readiness_status, deadlines_missed, readiness_score
            FROM students
            WHERE readiness_status <> 'READY' OR deadlines_missed >= 3
            ORDER BY deadlines_missed DESC, readiness_score ASC
            LIMIT 10
            """
        ).fetchall()

        at_risk_students = [
            AtRiskStudent(
                student_id=row["id"],
                name=row["name"],
                readiness_status=row["readiness_status"],
                reason=(
                    f"{row['deadlines_missed']} deadlines missed"
                    if row["deadlines_missed"] >= 3
                    else "Readiness score below healthy threshold"
                ),
                next_action=(
                    "TPC counseling + mandatory mock interview"
                    if row["deadlines_missed"] >= 3
                    else "Assign focused practice module"
                ),
            )
            for row in at_risk_rows
        ]

        communication_rows = conn.execute(
            """
            SELECT created_at, message
            FROM communications
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()
        top_recommendation_rows = conn.execute(
            """
            SELECT s.name AS student_name, c.company_name, c.role, a.match_score, a.selection_probability, a.status
            FROM applications a
            JOIN students s ON s.id = a.student_id
            JOIN companies c ON c.id = a.company_id
            WHERE a.status IN ('RECOMMENDED', 'OPEN')
            ORDER BY a.match_score DESC, a.selection_probability DESC
            LIMIT 8
            """
        ).fetchall()

        return AdminAnalyticsResponse(
            status="success",
            data={
                "cohort_distribution": CohortDistribution(
                    ready=int(distribution_row["ready"] or 0),
                    risky=int(distribution_row["risky"] or 0),
                    unprepared=int(distribution_row["unprepared"] or 0),
                ),
                "total_students": int(total_students),
                "total_companies": int(total_companies),
                "interventions_triggered": int(intervention_count),
                "autonomous_actions_today": int(communication_count + intervention_count),
                "applications_status_snapshot": status_snapshot,
                "at_risk_students": at_risk_students,
                "top_recommendations": [
                    TopRecommendation(
                        student_name=row["student_name"],
                        company=row["company_name"],
                        role=row["role"],
                        match_score=int(row["match_score"]),
                        selection_probability=int(row["selection_probability"]),
                        status=row["status"],
                    )
                    for row in top_recommendation_rows
                ],
                "communication_logs": [
                    CommunicationLog(timestamp=_display_time(row["created_at"]), action=row["message"])
                    for row in reversed(communication_rows)
                ],
                "flight_risk_alerts": flight_risk_alerts,
            },
        )

def get_student_journey(student_id: int) -> StudentJourneyResponse:
    initialize_engine()
    with _connect() as conn:
        _run_cycle_engine(conn)

        student_row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if student_row is None:
            raise ValueError(f"Student {student_id} not found")

        app_rows = conn.execute(
            """
            SELECT a.*, c.company_name, c.role
            FROM applications a
            JOIN companies c ON c.id = a.company_id
            WHERE a.student_id = ?
            ORDER BY a.match_score DESC, a.selection_probability DESC
            """,
            (student_id,),
        ).fetchall()

        intervention_rows = conn.execute(
            """
            SELECT intervention_type, details, status, created_at
            FROM interventions
            WHERE student_id = ?
            ORDER BY id DESC
            LIMIT 12
            """,
            (student_id,),
        ).fetchall()
        quiz_rows = conn.execute(
            """
            SELECT q.*, c.company_name, c.role
            FROM autonomous_quizzes q
            JOIN companies c ON c.id = q.company_id
            WHERE q.student_id = ?
            ORDER BY q.id DESC
            LIMIT 8
            """,
            (student_id,),
        ).fetchall()

        event_rows = conn.execute(
            """
            SELECT student_id, event_type, payload, event_time
            FROM journey_events
            WHERE student_id = ?
            ORDER BY id DESC
            LIMIT 12
            """,
            (student_id,),
        ).fetchall()

        profile = _build_profile_snapshot(student_row)

        return StudentJourneyResponse(
            status="success",
            data=StudentJourneyData(
                profile=profile,
                recommendations=[
                    {
                        "company": row["company_name"],
                        "role": row["role"],
                        "match_score": int(row["match_score"]),
                        "selection_probability": int(row["selection_probability"]),
                        "status": row["status"],
                        "reasoning": row["reasoning"],
                        "autonomous_action": row["autonomous_action"],
                    }
                    for row in app_rows
                ],
                interventions=[
                    StudentIntervention(
                        intervention_type=row["intervention_type"],
                        details=row["details"],
                        status=row["status"],
                        created_at=row["created_at"],
                    )
                    for row in intervention_rows
                ],
                autonomous_quizzes=[_build_autonomous_quiz_model(row) for row in quiz_rows],
                journey_events=[
                    StudentJourneyRecord(
                        student_id=row["student_id"],
                        event_type=row["event_type"],
                        payload=_from_json(row["payload"], {}),
                        event_time=row["event_time"],
                    )
                    for row in event_rows
                ],
            ),
        )


def get_company_requirements() -> CompanyRequirementsResponse:
    initialize_engine()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, company_name, role, min_cgpa, max_backlogs, one_job_policy, required_skills, deadline
            FROM companies
            WHERE active = 1
            ORDER BY company_name
            """
        ).fetchall()

        return CompanyRequirementsResponse(
            status="success",
            data=[
                CompanyRequirementRecord(
                    id=row["id"],
                    company_name=row["company_name"],
                    role=row["role"],
                    min_cgpa=float(row["min_cgpa"]),
                    max_backlogs=int(row["max_backlogs"]),
                    one_job_policy=bool(row["one_job_policy"]),
                    required_skills=_from_json(row["required_skills"], []),
                    deadline=row["deadline"],
                )
                for row in rows
            ],
        )


def get_quiz_detail(quiz_token: str) -> QuizDetailResponse:
    initialize_engine()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT q.*, c.company_name, c.role
            FROM autonomous_quizzes q
            JOIN companies c ON c.id = q.company_id
            WHERE q.token = ?
            LIMIT 1
            """,
            (quiz_token,),
        ).fetchone()
        if row is None:
            raise ValueError("Quiz not found")

        conn.execute(
            """
            UPDATE autonomous_quizzes
            SET status = CASE WHEN status = 'ASSIGNED' THEN 'OPENED' ELSE status END,
                updated_at = ?
            WHERE id = ?
            """,
            (_now_iso(), row["id"]),
        )
        refreshed = conn.execute(
            """
            SELECT q.*, c.company_name, c.role
            FROM autonomous_quizzes q
            JOIN companies c ON c.id = q.company_id
            WHERE q.id = ?
            """,
            (row["id"],),
        ).fetchone()
        return QuizDetailResponse(status="success", data=_build_autonomous_quiz_model(refreshed))


def _apply_simulation_action_in_conn(
    conn: sqlite3.Connection,
    request: SimulationActionRequest,
    *,
    run_cycle_after: bool,
) -> SimulationActionResult:
    student_row = conn.execute("SELECT * FROM students WHERE id = ?", (request.student_id,)).fetchone()
    if student_row is None:
        raise ValueError(f"Student {request.student_id} not found")

    action_type = request.action_type
    skills = _from_json(student_row["skills"], [])
    verified_skills = _from_json(student_row["verified_skills"], [])
    effect = ""
    payload: dict[str, Any] = {"action_type": action_type}

    if action_type == "MISS_DEADLINE":
        new_count = int(student_row["deadlines_missed"]) + 1
        conn.execute("UPDATE students SET deadlines_missed = ? WHERE id = ?", (new_count, request.student_id))
        effect = f"Deadline misses increased to {new_count}."
        payload["deadlines_missed"] = new_count
        _create_communication_if_needed(
            conn,
            target_group=f"STUDENT:{request.student_id}",
            message=f"Simulation: deadline missed count moved to {new_count}.",
        )

    elif action_type == "ADD_SKILL":
        if not isinstance(request.value, str) or not request.value.strip():
            raise ValueError("ADD_SKILL requires a non-empty string value.")
        skill = request.value.strip()
        if skill not in skills:
            skills.append(skill)
            conn.execute("UPDATE students SET skills = ? WHERE id = ?", (_to_json(skills), request.student_id))
            effect = f"Skill '{skill}' added to student profile."
        else:
            effect = f"Skill '{skill}' already present."
        payload["skill"] = skill

    elif action_type == "VERIFY_SKILL":
        if not isinstance(request.value, str) or not request.value.strip():
            raise ValueError("VERIFY_SKILL requires a non-empty string value.")
        skill = request.value.strip()
        if skill not in verified_skills:
            verified_skills.append(skill)
        if skill not in skills:
            skills.append(skill)
        conn.execute(
            "UPDATE students SET skills = ?, verified_skills = ? WHERE id = ?",
            (_to_json(skills), _to_json(verified_skills), request.student_id),
        )
        effect = f"Skill '{skill}' marked as AI-verified."
        payload["skill"] = skill

    elif action_type == "UPDATE_MOCK_SCORE":
        if not isinstance(request.value, int):
            raise ValueError("UPDATE_MOCK_SCORE requires integer value in range 0-100.")
        score = max(0, min(100, request.value))
        conn.execute("UPDATE students SET mock_score = ? WHERE id = ?", (score, request.student_id))
        effect = f"Mock interview score updated to {score}."
        payload["mock_score"] = score

    elif action_type == "UPDATE_INTERVIEW_SCORE":
        if not isinstance(request.value, int):
            raise ValueError("UPDATE_INTERVIEW_SCORE requires integer value in range 0-100.")
        score = max(0, min(100, request.value))
        conn.execute("UPDATE students SET interview_score = ? WHERE id = ?", (score, request.student_id))
        effect = f"Interview score updated to {score}."
        payload["interview_score"] = score

    elif action_type == "SET_ACCEPTED_OFFER":
        if not isinstance(request.value, str) or not request.value.strip():
            raise ValueError("SET_ACCEPTED_OFFER requires non-empty offer string.")
        offer = request.value.strip()
        conn.execute(
            "UPDATE students SET accepted_offer = ?, offer_status = 'ACCEPTED' WHERE id = ?",
            (offer, request.student_id),
        )
        effect = f"Accepted offer set to '{offer}'."
        payload["accepted_offer"] = offer

    elif action_type == "CLEAR_ACCEPTED_OFFER":
        conn.execute(
            "UPDATE students SET accepted_offer = NULL, offer_status = 'NONE' WHERE id = ?",
            (request.student_id,),
        )
        effect = "Accepted offer cleared."

    else:
        raise ValueError(f"Unsupported action type: {action_type}")

    payload.update(request.metadata)
    _append_journey_event(
        conn,
        student_id=request.student_id,
        event_type=f"simulation_{action_type.lower()}",
        payload=payload,
    )

    if run_cycle_after:
        _run_cycle_engine(conn)

    updated_row = conn.execute("SELECT * FROM students WHERE id = ?", (request.student_id,)).fetchone()
    return SimulationActionResult(
        student_id=request.student_id,
        action_type=action_type,
        effect=effect,
        profile=_build_profile_snapshot(updated_row),
    )


def apply_simulation_action(request: SimulationActionRequest) -> SimulationActionResponse:
    initialize_engine()
    with _connect() as conn:
        result = _apply_simulation_action_in_conn(conn, request, run_cycle_after=True)
        return SimulationActionResponse(status="success", result=result)


def run_what_if_trajectory(request: WhatIfTrajectoryRequest) -> WhatIfTrajectoryResponse:
    initialize_engine()
    with _connect() as conn:
        student_row = conn.execute("SELECT * FROM students WHERE id = ?", (request.student_id,)).fetchone()
        if student_row is None:
            raise ValueError(f"Student {request.student_id} not found")

        companies = _fetch_companies(conn)
        base_student = {
            **dict(student_row),
            "skills": _from_json(student_row["skills"], []),
            "verified_skills": _from_json(student_row["verified_skills"], []),
        }
        simulated_student, profile_delta = _apply_what_if_prompt(base_student, request.prompt, companies)

        base_profile = _build_profile_snapshot_from_student(base_student)
        simulated_profile = _build_profile_snapshot_from_student(simulated_student)

        impacts: list[WhatIfCompanyImpact] = []
        for company in companies:
            base_eval = _evaluate_company_for_student(student=base_student, company=company, prompt="")
            simulated_eval = _evaluate_company_for_student(
                student=simulated_student,
                company=company,
                prompt=request.prompt,
            )

            impacts.append(
                WhatIfCompanyImpact(
                    company=company["company_name"],
                    role=company["role"],
                    base_match_score=base_eval["match_score"],
                    simulated_match_score=simulated_eval["match_score"],
                    base_selection_probability=base_eval["selection_probability"],
                    simulated_selection_probability=simulated_eval["selection_probability"],
                    delta_probability=simulated_eval["selection_probability"] - base_eval["selection_probability"],
                    base_decision=base_eval["decision"],
                    simulated_decision=simulated_eval["decision"],
                    key_reasoning=simulated_eval["reasoning"],
                )
            )

        impacts.sort(key=lambda impact: (abs(impact.delta_probability), impact.simulated_selection_probability), reverse=True)

        if impacts:
            best_gain = max(impacts, key=lambda impact: impact.delta_probability)
            biggest_drop = min(impacts, key=lambda impact: impact.delta_probability)
            summary_parts = []
            if best_gain.delta_probability > 0:
                summary_parts.append(
                    f"Highest gain: {best_gain.company} {best_gain.role} ({best_gain.base_selection_probability}% -> "
                    f"{best_gain.simulated_selection_probability}%, +{best_gain.delta_probability})."
                )
            if biggest_drop.delta_probability < 0:
                summary_parts.append(
                    f"Biggest drop: {biggest_drop.company} {biggest_drop.role} ({biggest_drop.base_selection_probability}% -> "
                    f"{biggest_drop.simulated_selection_probability}%, {biggest_drop.delta_probability})."
                )
            if not summary_parts:
                summary_parts.append("Scenario caused minimal ranking shifts; core readiness remained stable.")
            summary = " ".join(summary_parts)
        else:
            summary = "No active companies found for simulation."

        return WhatIfTrajectoryResponse(
            status="success",
            data={
                "student_id": request.student_id,
                "prompt": request.prompt,
                "base_profile": base_profile,
                "simulated_profile": simulated_profile,
                "profile_delta": profile_delta,
                "summary": summary,
                "impacts": impacts,
            },
        )


def run_demo_showcase() -> DemoShowcaseResponse:
    initialize_engine()
    before_admin = get_admin_analytics().data

    steps: list[str] = []
    scenario_actions = [
        SimulationActionRequest(student_id=7, action_type="MISS_DEADLINE"),
        SimulationActionRequest(student_id=8, action_type="UPDATE_MOCK_SCORE", value=78),
        SimulationActionRequest(student_id=8, action_type="VERIFY_SKILL", value="Python"),
        SimulationActionRequest(student_id=8, action_type="ADD_SKILL", value="FastAPI"),
        SimulationActionRequest(student_id=6, action_type="SET_ACCEPTED_OFFER", value="Atlassian (Accepted)"),
    ]

    with _connect() as conn:
        for action in scenario_actions:
            result = _apply_simulation_action_in_conn(conn, action, run_cycle_after=False)
            steps.append(f"{action.action_type} -> Student {action.student_id}: {result.effect}")

        summary, _, _ = _run_cycle_engine(conn)

    after_admin = get_admin_analytics().data
    live_after = get_live_insights().data

    delta_interventions = after_admin.interventions_triggered - before_admin.interventions_triggered
    delta_actions = after_admin.autonomous_actions_today - before_admin.autonomous_actions_today
    delta_risky = after_admin.cohort_distribution.risky - before_admin.cohort_distribution.risky
    delta_unprepared = after_admin.cohort_distribution.unprepared - before_admin.cohort_distribution.unprepared

    highlights = [
        f"Interventions changed by {delta_interventions:+d}.",
        f"Autonomous actions changed by {delta_actions:+d}.",
        f"Risky cohort changed by {delta_risky:+d}.",
        f"Unprepared cohort changed by {delta_unprepared:+d}.",
        f"Flight-risk alerts now: {len(live_after.flight_risk_alerts)}.",
    ]

    return DemoShowcaseResponse(
        status="success",
        data={
            "before": before_admin,
            "after": after_admin,
            "live_after": live_after,
            "steps_executed": steps,
            "cycle_summary": summary,
            "highlighted_changes": highlights,
        },
    )
