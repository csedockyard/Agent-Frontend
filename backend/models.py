from typing import Any, Literal

from pydantic import BaseModel, Field


class EligibilityEnforced(BaseModel):
    total_scanned: int
    eligible_unlocked: int
    ineligible_blocked: int


class ActiveCampaigns(BaseModel):
    company: str
    eligibility_enforced: EligibilityEnforced


class FlightRiskAlert(BaseModel):
    student_name: str
    current_offer: str
    risk_level: str
    agent_reasoning: str
    autonomous_action: str


class CommunicationLog(BaseModel):
    timestamp: str
    action: str


class DashboardData(BaseModel):
    active_campaigns: ActiveCampaigns
    flight_risk_alerts: list[FlightRiskAlert]
    communication_logs: list[CommunicationLog]


class DashboardLiveInsightsResponse(BaseModel):
    status: str
    data: DashboardData


class StudentJourneyRecord(BaseModel):
    student_id: int
    event_type: str
    payload: dict[str, Any]
    event_time: str


class CompanyRequirementRecord(BaseModel):
    id: int
    company_name: str
    role: str
    min_cgpa: float
    max_backlogs: int
    one_job_policy: bool
    required_skills: list[str]
    deadline: str


class RecommendationInsight(BaseModel):
    company: str
    role: str
    match_score: int
    selection_probability: int
    status: str
    reasoning: str
    autonomous_action: str


class StudentIntervention(BaseModel):
    intervention_type: str
    details: str
    status: str
    created_at: str


class StudentProfileSnapshot(BaseModel):
    id: int
    name: str
    section: str
    cgpa: float
    backlogs: int
    skills: list[str]
    verified_skills: list[str]
    readiness_score: int
    readiness_status: Literal["READY", "RISKY", "UNPREPARED"]
    accepted_offer: str | None = None
    deadlines_missed: int


class StudentJourneyData(BaseModel):
    profile: StudentProfileSnapshot
    recommendations: list[RecommendationInsight]
    interventions: list[StudentIntervention]
    journey_events: list[StudentJourneyRecord]


class StudentJourneyResponse(BaseModel):
    status: str
    data: StudentJourneyData


class CohortDistribution(BaseModel):
    ready: int
    risky: int
    unprepared: int


class AtRiskStudent(BaseModel):
    student_id: int
    name: str
    readiness_status: str
    reason: str
    next_action: str


class AdminAnalyticsData(BaseModel):
    cohort_distribution: CohortDistribution
    total_students: int
    total_companies: int
    interventions_triggered: int
    autonomous_actions_today: int
    at_risk_students: list[AtRiskStudent]
    communication_logs: list[CommunicationLog]
    flight_risk_alerts: list[FlightRiskAlert]


class AdminAnalyticsResponse(BaseModel):
    status: str
    data: AdminAnalyticsData


class AgentDecision(BaseModel):
    student_id: int
    company_id: int
    decision: str
    match_score: int
    selection_probability: int
    reasoning: str
    autonomous_action: str


class DecisionCycleSummary(BaseModel):
    scanned_students: int
    recommendations_created: int
    blocked_applications: int
    mock_interviews_assigned: int
    tpc_alerts_triggered: int
    flight_risk_cases: int


class DecisionCycleResponse(BaseModel):
    status: str
    summary: DecisionCycleSummary
    decisions: list[AgentDecision] = Field(default_factory=list)


class CompanyRequirementsResponse(BaseModel):
    status: str
    data: list[CompanyRequirementRecord]
