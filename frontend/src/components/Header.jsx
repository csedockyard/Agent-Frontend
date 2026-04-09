const Header = ({ activeCampaign }) => {
  const eligibility = activeCampaign.eligibility_enforced;

  return (
    <header className="surface-card rounded-3xl p-6 md:p-7 flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500 font-semibold">Active Campaign</p>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mt-1">
            {activeCampaign.company} Recruitment Pulse
          </h2>
        </div>
        <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-emerald-700">
          Live Auto-Screening
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-2xl p-5 bg-gradient-to-br from-slate-100 to-slate-50 border border-slate-200/80">
          <p className="text-xs uppercase tracking-[0.14em] text-slate-500 font-semibold">Total Scanned</p>
          <p className="text-3xl font-bold text-slate-800 mt-2">{eligibility.total_scanned}</p>
          <p className="text-xs text-slate-500 mt-1">Profiles evaluated this cycle</p>
        </div>
        <div className="rounded-2xl p-5 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200/70">
          <p className="text-xs uppercase tracking-[0.14em] text-emerald-700 font-semibold">
            Eligible Unlocked
          </p>
          <p className="text-3xl font-bold text-emerald-700 mt-2">{eligibility.eligible_unlocked}</p>
          <p className="text-xs text-emerald-700/80 mt-1">Students immediately notified</p>
        </div>
        <div className="rounded-2xl p-5 bg-gradient-to-br from-rose-50 to-orange-50 border border-rose-200/70">
          <p className="text-xs uppercase tracking-[0.14em] text-rose-700 font-semibold">
            Ineligible Blocked
          </p>
          <p className="text-3xl font-bold text-rose-700 mt-2">{eligibility.ineligible_blocked}</p>
          <p className="text-xs text-rose-700/80 mt-1">Applications filtered by rules</p>
        </div>
      </div>
    </header>
  );
};

export default Header;
