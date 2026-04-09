const OpportunityList = ({ communicationLogs }) => {
  return (
    <section className="surface-card rounded-3xl overflow-hidden flex flex-col h-full min-h-[420px] xl:min-h-[740px]">
      <div className="p-6 border-b border-slate-200/70 bg-gradient-to-r from-slate-50 to-white">
        <h2 className="text-xl font-bold text-slate-900 mb-2">Communication Stream</h2>
        <p className="text-sm text-slate-600">
          Automated notifications sent to eligible students for campaign urgency.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/45" style={{ scrollbarWidth: "thin" }}>
        {communicationLogs.length === 0 ? (
          <div className="text-center text-slate-500 py-8">No communication events found.</div>
        ) : (
          communicationLogs.map((log, index) => (
            <article
              key={`${log.timestamp}-${index}`}
              className="bg-white p-5 rounded-2xl border border-slate-200 shadow-[0_10px_30px_rgba(15,23,42,0.08)]"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="w-9 h-9 rounded-xl bg-teal-100 text-teal-700 text-xs font-bold flex items-center justify-center">
                    {index + 1}
                  </span>
                  <p className="text-sm font-semibold text-slate-900">Dispatch Event</p>
                </div>
                <span className="text-xs px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100 font-medium">
                  {log.timestamp}
                </span>
              </div>
              <p className="text-[15px] text-slate-700 mt-4 leading-relaxed">{log.action}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
};

export default OpportunityList;
