import { useEffect, useState } from "react";

import AILogFeed from "./AILogFeed";
import AnalyticsCharts from "./AnalyticsCharts";
import Header from "./Header";
import OpportunityList from "./OpportunityList";
import apiService from "../services/api";

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const response = await apiService.fetchDashboardData();
        setData(response);
      } catch (fetchError) {
        console.error("Failed to load dashboard data:", fetchError);
        setError("Could not fetch live insights from backend.");
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="app-shell min-h-screen flex items-center justify-center p-6">
        <div className="surface-card rounded-3xl px-8 py-10 flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-teal-600 animate-spin" />
          <p className="text-slate-600 font-medium tracking-wide">Syncing Live Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="app-shell min-h-screen flex items-center justify-center p-6">
        <div className="surface-card max-w-md rounded-3xl p-7 text-center">
          <h1 className="text-lg font-semibold text-rose-700 mb-2">Backend Connection Error</h1>
          <p className="text-sm text-slate-600">
            {error || "Live insights payload is unavailable."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell text-slate-900 antialiased p-4 md:p-7 xl:p-10 min-h-screen">
      <div className="max-w-[1320px] mx-auto space-y-6">
        <section className="fade-slide">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500 font-semibold">
            University Placement Intelligence
          </p>
          <h1 className="mt-2 text-3xl md:text-4xl font-bold text-slate-900">
            Autonomous Placement Command Center
          </h1>
          <p className="mt-2 text-sm md:text-base text-slate-600 max-w-2xl">
            Real-time campaign eligibility, communication telemetry, and flight-risk signals in one view.
          </p>
        </section>

        <div className="fade-slide delay-1">
          <Header activeCampaign={data.active_campaigns} />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
          <div className="xl:col-span-7 fade-slide delay-2">
            <OpportunityList communicationLogs={data.communication_logs} />
          </div>

          <div className="xl:col-span-5 space-y-6 flex flex-col fade-slide delay-3">
            <AILogFeed flightRiskAlerts={data.flight_risk_alerts} />
            <AnalyticsCharts activeCampaign={data.active_campaigns} />
          </div>
        </div>
      </div>
    </div>
  );
}
