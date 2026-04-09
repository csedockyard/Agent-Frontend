from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.models import (
    AdminAnalyticsResponse,
    AgentDecision,
    AtRiskStudent,
    CohortDistribution,
    CommunicationLog,
    CompanyRequirementRecord,
    CompanyRequirementsResponse,
    DashboardLiveInsightsResponse,
    DecisionCycleResponse,
    DecisionCycleSummary,
    FlightRiskAlert,
    StudentIntervention,
    StudentJourneyData,
    StudentJourneyRecord,
    StudentJourneyResponse,
    StudentProfileSnapshot,
)

DB_PATH = Path(__file__).resolve().parent / "placementpro.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
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


def initialize_engine() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
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
            """
        )

        student_count = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]
        if student_count == 0:
            _seed_initial_data(conn)


def _seed_initial_data(conn: sqlite3.Connection) -> None:
    students = [
        {
            "id": 1,
            "name": "Umanshu Manan",
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
            id, name, section, cgpa, backlogs, skills, verified_skills,
            resume_uploads, mock_score, interview_score, deadlines_missed,
            accepted_offer, offer_status
        ) VALUES (
            :id, :name, :section, :cgpa, :backlogs, :skills, :verified_skills,
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
              AND a.status IN ('RECOMMENDED', 'OPEN')
            ORDER BY a.match_score DESC, a.selection_probability DESC
            LIMIT 1
            """,
            (student["id"],),
        ).fetchone()

        if not best_alt:
            continue

        if best_alt["company_name"] in student["accepted_offer"]:
            continue

        risk_percent = min(99, 55 + max(0, best_alt["match_score"] - 80) * 2 + (student["mock_score"] // 8))
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
                action = "Policy Agent blocked application."
                _upsert_application(
                    conn,
                    student_id=student["id"],
                    company_id=company["id"],
                    status="BLOCKED",
                    match_score=match_score,
                    selection_probability=selection_probability,
                    risk_tag=readiness_status,
                    reasoning=f"Policy & Eligibility Agent: {policy_reason_text}",
                    autonomous_action=action,
                )
                decisions.append(
                    AgentDecision(
                        student_id=student["id"],
                        company_id=company["id"],
                        decision="BLOCKED",
                        match_score=match_score,
                        selection_probability=selection_probability,
                        reasoning=f"Policy & Eligibility Agent: {policy_reason_text}",
                        autonomous_action=action,
                    )
                )
                continue

            decision = "RECOMMENDED" if match_score >= 90 else "OPEN"
            action_items: list[str] = []

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

            reasoning = (
                f"Matching Agent: {match_reasoning} "
                f"Predictive Agent: selection chance {selection_probability}% and readiness {readiness_status}. "
                "Policy Agent: eligible."
            )
            action = " ".join(action_items) if action_items else "No autonomous action required."

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
                "at_risk_students": at_risk_students,
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

        profile = StudentProfileSnapshot(
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
