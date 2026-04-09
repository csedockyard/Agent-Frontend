from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.responses import FileResponse

from dotenv import load_dotenv

from backend.agent import (
    apply_simulation_action,
    get_admin_analytics,
    get_company_requirements,
    get_live_insights,
    get_quiz_detail,
    get_student_journey,
    initialize_engine,
    run_demo_showcase,
    run_agentic_cycle,
    run_what_if_trajectory,
)
from backend.models import (
    AdminAnalyticsResponse,
    CompanyRequirementsResponse,
    DashboardLiveInsightsResponse,
    DemoShowcaseResponse,
    DecisionCycleResponse,
    QuizDetailResponse,
    SimulationActionRequest,
    SimulationActionResponse,
    StudentJourneyResponse,
    WhatIfTrajectoryRequest,
    WhatIfTrajectoryResponse,
)

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="PlacementPro Intelligence Hub")
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

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


@app.post("/api/simulations/apply-action", response_model=SimulationActionResponse)
def simulation_apply_action(request: SimulationActionRequest) -> SimulationActionResponse:
    try:
        return apply_simulation_action(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/simulations/what-if", response_model=WhatIfTrajectoryResponse)
def simulation_what_if(request: WhatIfTrajectoryRequest) -> WhatIfTrajectoryResponse:
    try:
        return run_what_if_trajectory(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo/one-click", response_model=DemoShowcaseResponse)
def demo_one_click() -> DemoShowcaseResponse:
    return run_demo_showcase()


@app.get("/api/quizzes/{quiz_token}", response_model=QuizDetailResponse)
def quiz_detail(quiz_token: str) -> QuizDetailResponse:
    try:
        return get_quiz_detail(quiz_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def app_index():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "ok"}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    if FRONTEND_DIST.exists():
        candidate = (FRONTEND_DIST / full_path).resolve()
        dist_root = FRONTEND_DIST.resolve()
        if str(candidate).startswith(str(dist_root)) and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)

        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    raise HTTPException(status_code=404, detail=f"Path '{full_path}' not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
# trigger reload
