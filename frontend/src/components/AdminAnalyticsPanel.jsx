const DISTRIBUTION_META = {
  ready: {
    label: "Ready",
    bar: "bg-emerald-500",
    chip: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  risky: {
    label: "Risky",
    bar: "bg-amber-500",
    chip: "bg-amber-50 text-amber-700 border-amber-200",
  },
  unprepared: {
    label: "Unprepared",
    bar: "bg-rose-500",
    chip: "bg-rose-50 text-rose-700 border-rose-200",
  },
};

const formatStatusChip = (status) => {
  const lower = String(status || "").toLowerCase();
  return DISTRIBUTION_META[lower] || DISTRIBUTION_META.risky;
};

export default function AdminAnalyticsPanel({ data }) {
  const totalDistribution = Math.max(
    1,
    data.cohort_distribution.ready + data.cohort_distribution.risky + data.cohort_distribution.unprepared,
  );

  const summaryCards = [
    {
      label: "Total Students",
      value: data.total_students,
      tone: "from-slate-100 to-slate-50 border-slate-200 text-slate-900",
    },
    {
      label: "Active Companies",
      value: data.total_companies,
      tone: "from-blue-50 to-cyan-50 border-blue-200 text-blue-900",
    },
    {
      label: "Interventions",
      value: data.interventions_triggered,
      tone: "from-indigo-50 to-violet-50 border-indigo-200 text-indigo-900",
    },
    {
      label: "Autonomous Actions",
      value: data.autonomous_actions_today,
      tone: "from-teal-50 to-emerald-50 border-teal-200 text-teal-900",
    },
  ];
  const statusSnapshot = Object.entries(data.applications_status_snapshot || {});

  return (
    <section className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <article
            key={card.label}
            className={`surface-card rounded-2xl p-5 border bg-gradient-to-br ${card.tone}`}
          >
            <p className="text-xs uppercase tracking-[0.14em] opacity-80 font-semibold">{card.label}</p>
            <p className="text-3xl font-bold mt-2">{card.value}</p>
          </article>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <article className="surface-card rounded-3xl p-6 xl:col-span-5">
          <h2 className="text-xl font-bold text-slate-900">Cohort Readiness</h2>
          <p className="text-sm text-slate-600 mt-1">Current distribution of student preparedness.</p>
          <div className="space-y-4 mt-6">
            {Object.entries(data.cohort_distribution).map(([key, value]) => {
              const meta = DISTRIBUTION_META[key];
              const width = `${Math.max(6, Math.round((value / totalDistribution) * 100))}%`;
              return (
                <div key={key}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold text-slate-700">{meta.label}</p>
                    <span
                      className={`text-xs border rounded-full px-2.5 py-1 font-semibold ${meta.chip}`}
                    >
                      {value}
                    </span>
                  </div>
                  <div className="h-2.5 bg-slate-200 rounded-full overflow-hidden">
                    <div className={`h-full ${meta.bar}`} style={{ width }} />
                  </div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="surface-card rounded-3xl p-6 xl:col-span-7">
          <h2 className="text-xl font-bold text-slate-900">At-Risk Students</h2>
          <p className="text-sm text-slate-600 mt-1">Students requiring immediate interventions.</p>
          <div className="mt-5 space-y-3 max-h-[320px] overflow-y-auto pr-1">
            {data.at_risk_students.length === 0 ? (
              <p className="text-slate-500 text-sm">No students flagged at the moment.</p>
            ) : (
              data.at_risk_students.map((student) => {
                const chip = formatStatusChip(student.readiness_status);
                return (
                  <article key={student.student_id} className="bg-white border border-slate-200 rounded-2xl p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-semibold text-slate-900">{student.name}</h3>
                      <span className={`text-xs border rounded-full px-2 py-1 font-semibold ${chip.chip}`}>
                        {student.readiness_status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 mt-2">{student.reason}</p>
                    <p className="text-sm text-teal-700 mt-1">
                      <span className="font-semibold">Next Action:</span> {student.next_action}
                    </p>
                  </article>
                );
              })
            )}
          </div>
        </article>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <article className="surface-card rounded-3xl p-6 xl:col-span-6">
          <h2 className="text-xl font-bold text-slate-900">Unified Communication</h2>
          <p className="text-sm text-slate-600 mt-1">Targeted nudges and alerts generated by the agents.</p>
          <div className="mt-5 space-y-3 max-h-[300px] overflow-y-auto pr-1">
            {data.communication_logs.length === 0 ? (
              <p className="text-slate-500 text-sm">No communication events recorded yet.</p>
            ) : (
              data.communication_logs.map((log, index) => (
                <article key={`${log.timestamp}-${index}`} className="bg-white border border-slate-200 rounded-2xl p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-800">Dispatch #{index + 1}</p>
                    <span className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                      {log.timestamp}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mt-2">{log.action}</p>
                </article>
              ))
            )}
          </div>
        </article>

        <article className="surface-card rounded-3xl p-6 xl:col-span-6">
          <h2 className="text-xl font-bold text-slate-900">Flight-Risk Intelligence</h2>
          <p className="text-sm text-slate-600 mt-1">Offer-drop prediction and waitlist automation.</p>
          <div className="mt-5 space-y-3 max-h-[300px] overflow-y-auto pr-1">
            {data.flight_risk_alerts.length === 0 ? (
              <p className="text-slate-500 text-sm">No flight-risk alerts right now.</p>
            ) : (
              data.flight_risk_alerts.map((alert, index) => (
                <article key={`${alert.student_name}-${index}`} className="bg-white border border-rose-200 rounded-2xl p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="font-semibold text-slate-900">{alert.student_name}</h3>
                    <span className="text-xs px-2 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
                      {alert.risk_level}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Current Offer: {alert.current_offer}</p>
                  <p className="text-sm text-slate-600 mt-2">{alert.agent_reasoning}</p>
                  <p className="text-sm text-emerald-700 mt-2">
                    <span className="font-semibold">Autonomous Action:</span> {alert.autonomous_action}
                  </p>
                </article>
              ))
            )}
          </div>
        </article>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <article className="surface-card rounded-3xl p-6 xl:col-span-4">
          <h2 className="text-xl font-bold text-slate-900">Application Status Mix</h2>
          <p className="text-sm text-slate-600 mt-1">Distribution across all AI decisions.</p>
          <div className="mt-4 space-y-2">
            {statusSnapshot.length === 0 ? (
              <p className="text-sm text-slate-500">No application status data yet.</p>
            ) : (
              statusSnapshot.map(([status, count]) => (
                <div key={status} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <span className="text-sm font-semibold text-slate-700">{status}</span>
                  <span className="text-sm text-slate-900 font-bold">{count}</span>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="surface-card rounded-3xl p-6 xl:col-span-8">
          <h2 className="text-xl font-bold text-slate-900">Top Recommendation Feed</h2>
          <p className="text-sm text-slate-600 mt-1">Highest confidence student-company matches right now.</p>
          <div className="mt-4 space-y-3 max-h-[320px] overflow-y-auto pr-1">
            {data.top_recommendations.length === 0 ? (
              <p className="text-sm text-slate-500">No top recommendations available yet.</p>
            ) : (
              data.top_recommendations.map((item, index) => (
                <article key={`${item.student_name}-${item.company}-${index}`} className="bg-white border border-slate-200 rounded-2xl p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900">{item.student_name}</p>
                      <p className="text-xs text-slate-500">{item.company} · {item.role}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-1 rounded-full border border-blue-200 bg-blue-50 text-blue-700 font-semibold">
                        Match {item.match_score}%
                      </span>
                      <span className="text-xs px-2 py-1 rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700 font-semibold">
                        Select {item.selection_probability}%
                      </span>
                      <span className="text-xs px-2 py-1 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 font-semibold">
                        {item.status}
                      </span>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        </article>
      </div>
    </section>
  );
}
