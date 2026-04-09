const AILogFeed = ({ flightRiskAlerts }) => {
  return (
    <section className="surface-card rounded-3xl p-6 flex-shrink-0">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span className="text-xs px-2 py-1 rounded-full bg-rose-100 text-rose-700 border border-rose-200 uppercase tracking-wider font-semibold">
              AI
            </span>
            Flight Risk Alerts
          </h2>
          <p className="text-xs text-slate-500 mt-1">Live autonomous replacement intelligence</p>
        </div>
        <span className="bg-rose-100 text-rose-800 text-xs px-2.5 py-1 rounded-full font-semibold border border-rose-200">
          High Priority
        </span>
      </div>

      <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-sm space-y-3">
        {flightRiskAlerts.length === 0 ? (
          <p className="text-slate-500">No active flight risk alerts right now.</p>
        ) : (
          flightRiskAlerts.map((alert, index) => (
            <article
              key={index}
              className="bg-white border border-slate-200 rounded-2xl p-4 shadow-[0_12px_30px_rgba(15,23,42,0.08)]"
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold text-slate-900 text-base">{alert.student_name}</h3>
                <span className="text-xs px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-semibold">
                  {alert.risk_level}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-2">Current Offer: {alert.current_offer}</p>
              <p className="text-[13px] text-slate-700 mt-3 leading-relaxed">
                <span className="font-semibold">Agent Reasoning:</span> {alert.agent_reasoning}
              </p>
              <p className="text-[13px] text-teal-700 mt-3 leading-relaxed">
                <span className="font-semibold">Autonomous Action:</span> {alert.autonomous_action}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
};

export default AILogFeed;
