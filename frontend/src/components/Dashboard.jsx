import { useEffect, useState } from "react";

import AILogFeed from "./AILogFeed";
import AdminAnalyticsPanel from "./AdminAnalyticsPanel";
import AnalyticsCharts from "./AnalyticsCharts";
import Header from "./Header";
import OpportunityList from "./OpportunityList";
import StudentJourneyPanel from "./StudentJourneyPanel";
import apiService from "../services/api";

const VIEW_META = {
  live: {
    kicker: "University Placement Intelligence",
    title: "Autonomous Placement Command Center",
    description:
      "Real-time campaign eligibility, communication telemetry, and flight-risk signals in one view.",
  },
  admin: {
    kicker: "TPC Admin Intelligence",
    title: "Centralized Cohort Analytics",
    description:
      "Monitor readiness distribution, at-risk students, interventions, and all autonomous communication actions.",
  },
  journey: {
    kicker: "Student Journey Intelligence",
    title: "Skill-to-Offer Progress Tracker",
    description:
      "Inspect every touchpoint from profile readiness to recommendations, interventions, and timeline events.",
  },
};

const VIEW_BUTTONS = [
  { id: "live", label: "Live Command Center" },
  { id: "admin", label: "Admin Analytics" },
  { id: "journey", label: "Student Journey" },
];

function LoadingCard({ label }) {
  return (
    <article className="surface-card rounded-3xl px-8 py-10 flex flex-col items-center gap-4">
      <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-teal-600 animate-spin" />
      <p className="text-slate-600 font-medium tracking-wide">{label}</p>
    </article>
  );
}

function ErrorCard({ message }) {
  return (
    <article className="surface-card rounded-3xl p-7 text-center border border-rose-200">
      <h2 className="text-lg font-semibold text-rose-700 mb-2">Backend Connection Error</h2>
      <p className="text-sm text-slate-600">{message}</p>
    </article>
  );
}

export default function Dashboard() {
  const [activeView, setActiveView] = useState("live");

  const [liveLoading, setLiveLoading] = useState(true);
  const [liveError, setLiveError] = useState("");
  const [liveData, setLiveData] = useState(null);

  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState("");
  const [adminData, setAdminData] = useState(null);

  const [journeyLoading, setJourneyLoading] = useState(false);
  const [journeyError, setJourneyError] = useState("");
  const [journeyData, setJourneyData] = useState(null);
  const [selectedStudentId, setSelectedStudentId] = useState(1);

  const [cycleRunning, setCycleRunning] = useState(false);
  const [cycleError, setCycleError] = useState("");
  const [cycleSummary, setCycleSummary] = useState(null);

  const [simulationBusy, setSimulationBusy] = useState(false);
  const [simulationError, setSimulationError] = useState("");
  const [simulationSuccess, setSimulationSuccess] = useState("");
  const [whatIfBusy, setWhatIfBusy] = useState(false);
  const [whatIfError, setWhatIfError] = useState("");
  const [whatIfResult, setWhatIfResult] = useState(null);

  const [demoRunning, setDemoRunning] = useState(false);
  const [demoError, setDemoError] = useState("");
  const [demoData, setDemoData] = useState(null);

  const loadLiveData = async () => {
    setLiveLoading(true);
    setLiveError("");
    try {
      const response = await apiService.fetchDashboardData();
      setLiveData(response);
    } catch (error) {
      console.error("Failed to load live dashboard data:", error);
      setLiveError("Could not fetch live insights from backend.");
    } finally {
      setLiveLoading(false);
    }
  };

  const loadAdminData = async () => {
    setAdminLoading(true);
    setAdminError("");
    try {
      const response = await apiService.fetchAdminAnalytics();
      setAdminData(response);
    } catch (error) {
      console.error("Failed to load admin analytics:", error);
      setAdminError("Could not fetch admin analytics from backend.");
    } finally {
      setAdminLoading(false);
    }
  };

  const loadStudentJourney = async (studentId) => {
    setJourneyLoading(true);
    setJourneyError("");
    try {
      const response = await apiService.fetchStudentJourney(studentId);
      setJourneyData(response);
    } catch (error) {
      console.error("Failed to load student journey:", error);
      setJourneyError(`Could not fetch student journey for ID ${studentId}.`);
    } finally {
      setJourneyLoading(false);
    }
  };

  useEffect(() => {
    loadLiveData();
  }, []);

  useEffect(() => {
    if (activeView === "admin" && !adminData && !adminLoading) {
      loadAdminData();
    }
    if (activeView === "journey" && !journeyData && !journeyLoading) {
      loadStudentJourney(selectedStudentId);
    }
  }, [activeView]);

  const handleStudentChange = (studentId) => {
    setSelectedStudentId(studentId);
    setWhatIfError("");
    setWhatIfResult(null);
    loadStudentJourney(studentId);
  };

  const handleRunCycle = async () => {
    setCycleRunning(true);
    setCycleError("");
    try {
      const cycleResponse = await apiService.triggerAgentCycle();
      setCycleSummary(cycleResponse.summary);
      await refreshLoadedViews();
    } catch (error) {
      console.error("Failed to run agent cycle:", error);
      setCycleError("Unable to trigger autonomous cycle right now.");
    } finally {
      setCycleRunning(false);
    }
  };

  const refreshLoadedViews = async () => {
    await loadLiveData();
    if (activeView === "admin" || adminData) {
      await loadAdminData();
    }
    if (activeView === "journey" || journeyData) {
      await loadStudentJourney(selectedStudentId);
    }
  };

  const executeSimulation = async (actionType, value = null, metadata = {}) => {
    setSimulationBusy(true);
    setSimulationError("");
    setSimulationSuccess("");
    try {
      const result = await apiService.applySimulationAction({
        student_id: selectedStudentId,
        action_type: actionType,
        value,
        metadata,
      });
      setSimulationSuccess(result.effect);
      await refreshLoadedViews();
    } catch (error) {
      console.error("Simulation failed:", error);
      setSimulationError(error.message || "Simulation failed.");
    } finally {
      setSimulationBusy(false);
    }
  };

  const handleMissDeadline = async () => {
    await executeSimulation("MISS_DEADLINE");
  };

  const handleAddSkill = async (skill) => {
    await executeSimulation("ADD_SKILL", skill);
  };

  const handleVerifySkill = async (skill) => {
    await executeSimulation("VERIFY_SKILL", skill);
  };

  const handleUpdateMockScore = async (score) => {
    await executeSimulation("UPDATE_MOCK_SCORE", score);
  };

  const handleRunWhatIf = async (prompt) => {
    setWhatIfBusy(true);
    setWhatIfError("");
    try {
      const result = await apiService.runWhatIfTrajectory({
        student_id: selectedStudentId,
        prompt,
      });
      setWhatIfResult(result);
    } catch (error) {
      console.error("What-if simulation failed:", error);
      setWhatIfError(error.message || "What-if simulation failed.");
    } finally {
      setWhatIfBusy(false);
    }
  };

  const handleDemoMode = async () => {
    setDemoRunning(true);
    setDemoError("");
    try {
      const result = await apiService.runDemoOneClick();
      setDemoData(result);
      setCycleSummary(result.cycle_summary);
      await refreshLoadedViews();
    } catch (error) {
      console.error("Demo mode failed:", error);
      setDemoError(error.message || "Demo mode failed.");
    } finally {
      setDemoRunning(false);
    }
  };

  const meta = VIEW_META[activeView];

  return (
    <div className="app-shell text-slate-900 antialiased p-4 md:p-7 xl:p-10 min-h-screen">
      <div className="max-w-[1320px] mx-auto space-y-6">
        <section className="fade-slide">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500 font-semibold">{meta.kicker}</p>
          <h1 className="mt-2 text-3xl md:text-4xl font-bold text-slate-900">{meta.title}</h1>
          <p className="mt-2 text-sm md:text-base text-slate-600 max-w-3xl">{meta.description}</p>
        </section>

        <section className="surface-card rounded-3xl p-4 md:p-5 fade-slide delay-1">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {VIEW_BUTTONS.map((button) => (
                <button
                  key={button.id}
                  type="button"
                  onClick={() => setActiveView(button.id)}
                  className={
                    activeView === button.id
                      ? "px-4 py-2 rounded-xl text-sm font-semibold bg-slate-900 text-white"
                      : "px-4 py-2 rounded-xl text-sm font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }
                >
                  {button.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleRunCycle}
                disabled={cycleRunning}
                className="px-4 py-2 rounded-xl text-sm font-semibold bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-65 disabled:cursor-not-allowed"
              >
                {cycleRunning ? "Running Agent Cycle..." : "Run Agent Cycle"}
              </button>
              <button
                type="button"
                onClick={handleDemoMode}
                disabled={demoRunning}
                className="px-4 py-2 rounded-xl text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-65 disabled:cursor-not-allowed"
              >
                {demoRunning ? "Executing Demo..." : "One-Click Demo Mode"}
              </button>
            </div>
          </div>
          {cycleSummary && (
            <p className="mt-3 text-sm text-slate-600">
              Cycle Result: scanned {cycleSummary.scanned_students}, recommendations {cycleSummary.recommendations_created},
              blocked {cycleSummary.blocked_applications}, flight-risk cases {cycleSummary.flight_risk_cases}.
            </p>
          )}
          {cycleError && <p className="mt-3 text-sm text-rose-700">{cycleError}</p>}
          {demoError && <p className="mt-3 text-sm text-rose-700">{demoError}</p>}
        </section>

        {demoData && (
          <section className="surface-card rounded-3xl p-5 fade-slide delay-2">
            <h2 className="text-lg font-bold text-slate-900">Demo Impact Snapshot</h2>
            <p className="text-sm text-slate-600 mt-1">Before/after proof generated by one-click demo execution.</p>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
              <article className="bg-white border border-slate-200 rounded-2xl p-4">
                <p className="text-sm font-semibold text-slate-900">Steps Executed</p>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  {demoData.steps_executed.map((step, index) => (
                    <li key={`${step}-${index}`}>{index + 1}. {step}</li>
                  ))}
                </ul>
              </article>
              <article className="bg-white border border-slate-200 rounded-2xl p-4">
                <p className="text-sm font-semibold text-slate-900">Highlighted Changes</p>
                <ul className="mt-2 space-y-1 text-sm text-emerald-700">
                  {demoData.highlighted_changes.map((item, index) => (
                    <li key={`${item}-${index}`}>{index + 1}. {item}</li>
                  ))}
                </ul>
              </article>
            </div>
          </section>
        )}

        {activeView === "live" && (
          <section className="fade-slide delay-2">
            {liveLoading && <LoadingCard label="Syncing Live Dashboard..." />}
            {!liveLoading && liveError && <ErrorCard message={liveError} />}
            {!liveLoading && !liveError && liveData && (
              <div className="space-y-6">
                <Header activeCampaign={liveData.active_campaigns} />
                <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
                  <div className="xl:col-span-7">
                    <OpportunityList communicationLogs={liveData.communication_logs} />
                  </div>
                  <div className="xl:col-span-5 space-y-6 flex flex-col">
                    <AILogFeed flightRiskAlerts={liveData.flight_risk_alerts} />
                    <AnalyticsCharts activeCampaign={liveData.active_campaigns} />
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {activeView === "admin" && (
          <section className="fade-slide delay-2">
            {adminLoading && <LoadingCard label="Loading Admin Analytics..." />}
            {!adminLoading && adminError && <ErrorCard message={adminError} />}
            {!adminLoading && !adminError && adminData && <AdminAnalyticsPanel data={adminData} />}
          </section>
        )}

        {activeView === "journey" && (
          <section className="fade-slide delay-2">
            <StudentJourneyPanel
              loading={journeyLoading}
              error={journeyError}
              selectedStudentId={selectedStudentId}
              onStudentChange={handleStudentChange}
              data={journeyData}
              simulationBusy={simulationBusy}
              simulationError={simulationError}
              simulationSuccess={simulationSuccess}
              whatIfBusy={whatIfBusy}
              whatIfError={whatIfError}
              whatIfResult={whatIfResult}
              onMissDeadline={handleMissDeadline}
              onAddSkill={handleAddSkill}
              onUpdateMockScore={handleUpdateMockScore}
              onVerifySkill={handleVerifySkill}
              onRunWhatIf={handleRunWhatIf}
            />
          </section>
        )}
      </div>
    </div>
  );
}
