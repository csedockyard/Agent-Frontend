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


class QuizQuestion(BaseModel):
    question: str
    difficulty: str
    expected_topics: list[str]
    starter_hint: str


class AutonomousQuiz(BaseModel):
    quiz_id: int
    token: str
    company: str
    role: str
    topic: str
    delivery_status: str
    created_at: str
    questions: list[QuizQuestion]


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
    autonomous_quizzes: list[AutonomousQuiz]
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


class TopRecommendation(BaseModel):
    student_name: str
    company: str
    role: str
    match_score: int
    selection_probability: int
    status: str


class AdminAnalyticsData(BaseModel):
    cohort_distribution: CohortDistribution
    total_students: int
    total_companies: int
    interventions_triggered: int
    autonomous_actions_today: int
    applications_status_snapshot: dict[str, int]
    at_risk_students: list[AtRiskStudent]
    top_recommendations: list[TopRecommendation]
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


class SimulationActionRequest(BaseModel):
    student_id: int
    action_type: Literal[
        "MISS_DEADLINE",
        "ADD_SKILL",
        "VERIFY_SKILL",
        "UPDATE_MOCK_SCORE",
        "UPDATE_INTERVIEW_SCORE",
        "SET_ACCEPTED_OFFER",
        "CLEAR_ACCEPTED_OFFER",
    ]
    value: str | int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulationActionResult(BaseModel):
    student_id: int
    action_type: str
    effect: str
    profile: StudentProfileSnapshot


class SimulationActionResponse(BaseModel):
    status: str
    result: SimulationActionResult


class WhatIfTrajectoryRequest(BaseModel):
    student_id: int
    prompt: str = Field(min_length=3, max_length=500)


class WhatIfProfileDelta(BaseModel):
    skills_added: list[str] = Field(default_factory=list)
    verified_skills_added: list[str] = Field(default_factory=list)
    backlogs_delta: int = 0
    deadlines_missed_delta: int = 0
    mock_score_delta: int = 0
    interview_score_delta: int = 0
    accepted_offer_cleared: bool = False
    assumptions: list[str] = Field(default_factory=list)


class WhatIfCompanyImpact(BaseModel):
    company: str
    role: str
    base_match_score: int
    simulated_match_score: int
    base_selection_probability: int
    simulated_selection_probability: int
    delta_probability: int
    base_decision: str
    simulated_decision: str
    key_reasoning: str


class WhatIfTrajectoryData(BaseModel):
    student_id: int
    prompt: str
    base_profile: StudentProfileSnapshot
    simulated_profile: StudentProfileSnapshot
    profile_delta: WhatIfProfileDelta
    summary: str
    impacts: list[WhatIfCompanyImpact]


class WhatIfTrajectoryResponse(BaseModel):
    status: str
    data: WhatIfTrajectoryData


class DemoShowcaseData(BaseModel):
    before: AdminAnalyticsData
    after: AdminAnalyticsData
    live_after: DashboardData
    steps_executed: list[str]
    cycle_summary: DecisionCycleSummary
    highlighted_changes: list[str]


class DemoShowcaseResponse(BaseModel):
    status: str
    data: DemoShowcaseData


class QuizDetailResponse(BaseModel):
    status: str
    data: AutonomousQuiz
