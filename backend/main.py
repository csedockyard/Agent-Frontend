from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agent import (
    get_admin_analytics,
    get_company_requirements,
    get_live_insights,
    get_student_journey,
    initialize_engine,
    run_agentic_cycle,
)
from backend.models import (
    AdminAnalyticsResponse,
    CompanyRequirementsResponse,
    DashboardLiveInsightsResponse,
    DecisionCycleResponse,
    StudentJourneyResponse,
)

app = FastAPI(title="PlacementPro Intelligence Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    initialize_engine()


@app.get("/api/dashboard/live-insights", response_model=DashboardLiveInsightsResponse)
def dashboard_live_insights() -> DashboardLiveInsightsResponse:
    return get_live_insights()


@app.get("/api/admin/analytics", response_model=AdminAnalyticsResponse)
def admin_analytics() -> AdminAnalyticsResponse:
    return get_admin_analytics()


@app.get("/api/students/{student_id}/journey", response_model=StudentJourneyResponse)
def student_journey(student_id: int) -> StudentJourneyResponse:
    try:
        return get_student_journey(student_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/companies/requirements", response_model=CompanyRequirementsResponse)
def company_requirements() -> CompanyRequirementsResponse:
    return get_company_requirements()


@app.post("/api/agents/run-cycle", response_model=DecisionCycleResponse)
def trigger_agent_cycle() -> DecisionCycleResponse:
    return run_agentic_cycle()


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
