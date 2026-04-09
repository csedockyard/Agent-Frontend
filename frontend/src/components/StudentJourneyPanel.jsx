import { useState } from "react";

const JOURNEY_STUDENTS = [1, 2, 3, 4, 5, 6, 7, 8];

function statusTone(status) {
  if (status === "READY") {
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  }
  if (status === "UNPREPARED") {
    return "bg-rose-50 text-rose-700 border-rose-200";
  }
  return "bg-amber-50 text-amber-700 border-amber-200";
}

function recommendationTone(status) {
  if (status === "RECOMMENDED") {
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  }
  if (status === "BLOCKED") {
    return "bg-rose-50 text-rose-700 border-rose-200";
  }
  if (status === "AT_RISK") {
    return "bg-amber-50 text-amber-700 border-amber-200";
  }
  return "bg-blue-50 text-blue-700 border-blue-200";
}

export default function StudentJourneyPanel({
  loading,
  error,
  selectedStudentId,
  onStudentChange,
  data,
  simulationBusy,
  simulationError,
  simulationSuccess,
  whatIfBusy,
  whatIfError,
  whatIfResult,
  onMissDeadline,
  onAddSkill,
  onUpdateMockScore,
  onVerifySkill,
  onRunWhatIf,
}) {
  const [skillInput, setSkillInput] = useState("");
  const [verifySkillInput, setVerifySkillInput] = useState("");
  const [mockScoreInput, setMockScoreInput] = useState("70");
  const [whatIfPrompt, setWhatIfPrompt] = useState("What if I learn AWS and clear my backlog this weekend?");

  const submitSkill = (event) => {
    event.preventDefault();
    if (!skillInput.trim()) {
      return;
    }
    onAddSkill(skillInput.trim());
    setSkillInput("");
  };

  const submitVerifySkill = (event) => {
    event.preventDefault();
    if (!verifySkillInput.trim()) {
      return;
    }
    onVerifySkill(verifySkillInput.trim());
    setVerifySkillInput("");
  };

  const submitMockScore = (event) => {
    event.preventDefault();
    const parsed = Number(mockScoreInput);
    if (Number.isNaN(parsed)) {
      return;
    }
    onUpdateMockScore(parsed);
  };

  const submitWhatIf = (event) => {
    event.preventDefault();
    if (!whatIfPrompt.trim()) {
      return;
    }
    onRunWhatIf(whatIfPrompt.trim());
  };

  return (
    <section className="space-y-6">
      <article className="surface-card rounded-3xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Student Journey Console</h2>
            <p className="text-sm text-slate-600 mt-1">
              Track readiness, interventions, recommendations, and historical touchpoints.
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            Student ID
            <select
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-800 font-semibold"
              value={selectedStudentId}
              onChange={(event) => onStudentChange(Number(event.target.value))}
            >
              {JOURNEY_STUDENTS.map((id) => (
                <option value={id} key={id}>
                  {id}
                </option>
              ))}
            </select>
          </label>
        </div>
      </article>

      <article className="surface-card rounded-3xl p-6">
        <h3 className="text-lg font-bold text-slate-900">Scenario Simulation Controls</h3>
        <p className="text-sm text-slate-600 mt-1">
          Trigger real agent decisions by changing student behavior and readiness inputs.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 mt-4">
          <button
            type="button"
            onClick={onMissDeadline}
            disabled={simulationBusy}
            className="rounded-xl px-4 py-3 bg-rose-600 text-white font-semibold hover:bg-rose-700 disabled:opacity-60"
          >
            Miss Deadline
          </button>
          <form onSubmit={submitSkill} className="flex gap-2">
            <input
              className="rounded-xl border border-slate-300 px-3 py-2 text-sm w-full"
              value={skillInput}
              onChange={(event) => setSkillInput(event.target.value)}
              placeholder="Add skill (e.g. AWS)"
              disabled={simulationBusy}
            />
            <button
              type="submit"
              disabled={simulationBusy}
              className="rounded-xl px-3 py-2 bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:opacity-60"
            >
              Add
            </button>
          </form>
          <form onSubmit={submitVerifySkill} className="flex gap-2">
            <input
              className="rounded-xl border border-slate-300 px-3 py-2 text-sm w-full"
              value={verifySkillInput}
              onChange={(event) => setVerifySkillInput(event.target.value)}
              placeholder="Verify skill (e.g. Python)"
              disabled={simulationBusy}
            />
            <button
              type="submit"
              disabled={simulationBusy}
              className="rounded-xl px-3 py-2 bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-60"
            >
              Verify
            </button>
          </form>
          <form onSubmit={submitMockScore} className="flex gap-2">
            <input
              type="number"
              min="0"
              max="100"
              className="rounded-xl border border-slate-300 px-3 py-2 text-sm w-full"
              value={mockScoreInput}
              onChange={(event) => setMockScoreInput(event.target.value)}
              placeholder="Mock score"
              disabled={simulationBusy}
            />
            <button
              type="submit"
              disabled={simulationBusy}
              className="rounded-xl px-3 py-2 bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60"
            >
              Update
            </button>
          </form>
        </div>
        {simulationSuccess && <p className="mt-3 text-sm text-emerald-700 font-medium">{simulationSuccess}</p>}
        {simulationError && <p className="mt-3 text-sm text-rose-700 font-medium">{simulationError}</p>}
      </article>

      <article className="surface-card rounded-3xl p-6">
        <h3 className="text-lg font-bold text-slate-900">What-If Trajectory Engine</h3>
        <p className="text-sm text-slate-600 mt-1">
          Ask the agent how profile changes impact company-wise selection probability before you actually do them.
        </p>
        <form onSubmit={submitWhatIf} className="mt-4 space-y-3">
          <textarea
            className="w-full rounded-2xl border border-slate-300 bg-white p-3 text-sm min-h-[96px]"
            value={whatIfPrompt}
            onChange={(event) => setWhatIfPrompt(event.target.value)}
            placeholder="What if I learn AWS and clear my backlog this weekend?"
            disabled={whatIfBusy}
          />
          <button
            type="submit"
            disabled={whatIfBusy}
            className="rounded-xl px-4 py-2.5 bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800 disabled:opacity-60"
          >
            {whatIfBusy ? "Running What-If..." : "Run What-If Simulation"}
          </button>
        </form>
        {whatIfError && <p className="mt-3 text-sm text-rose-700 font-medium">{whatIfError}</p>}

        {whatIfResult && (
          <div className="mt-4 space-y-3">
            <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">Simulation Summary</p>
              <p className="text-sm text-slate-700 mt-2">{whatIfResult.summary}</p>
              {whatIfResult.profile_delta?.assumptions?.length > 0 && (
                <div className="mt-2 space-y-1">
                  {whatIfResult.profile_delta.assumptions.map((item, idx) => (
                    <p key={`${item}-${idx}`} className="text-xs text-slate-500">
                      Assumption {idx + 1}: {item}
                    </p>
                  ))}
                </div>
              )}
            </article>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
              <article className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500 font-semibold">Current Profile</p>
                <p className="text-sm text-slate-800 mt-2">
                  Readiness {whatIfResult.base_profile.readiness_status} ({whatIfResult.base_profile.readiness_score})
                </p>
                <p className="text-xs text-slate-600 mt-1">
                  Backlogs {whatIfResult.base_profile.backlogs} | Deadlines missed {whatIfResult.base_profile.deadlines_missed}
                </p>
              </article>
              <article className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-emerald-700 font-semibold">Simulated Profile</p>
                <p className="text-sm text-emerald-800 mt-2">
                  Readiness {whatIfResult.simulated_profile.readiness_status} ({whatIfResult.simulated_profile.readiness_score})
                </p>
                <p className="text-xs text-emerald-700 mt-1">
                  Backlogs {whatIfResult.simulated_profile.backlogs} | Deadlines missed {whatIfResult.simulated_profile.deadlines_missed}
                </p>
              </article>
            </div>

            <div className="space-y-2">
              {whatIfResult.impacts.map((impact, index) => (
                <article key={`${impact.company}-${impact.role}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{impact.company}</p>
                      <p className="text-xs text-slate-500">{impact.role}</p>
                    </div>
                    <span
                      className={
                        impact.delta_probability >= 0
                          ? "text-xs px-2 py-1 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 font-semibold"
                          : "text-xs px-2 py-1 rounded-full border border-rose-200 bg-rose-50 text-rose-700 font-semibold"
                      }
                    >
                      {impact.delta_probability >= 0 ? `+${impact.delta_probability}` : impact.delta_probability}% delta
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">
                    Probability: {impact.base_selection_probability}% {"->"} {impact.simulated_selection_probability}% | Status:{" "}
                    {impact.base_decision} {"->"} {impact.simulated_decision}
                  </p>
                  <p className="text-xs text-slate-500 mt-2">{impact.key_reasoning}</p>
                </article>
              ))}
            </div>
          </div>
        )}
      </article>

      {loading && (
        <article className="surface-card rounded-3xl p-8 text-center">
          <p className="text-slate-600 font-medium">Fetching journey timeline...</p>
        </article>
      )}

      {!loading && error && (
        <article className="surface-card rounded-3xl p-8 text-center border border-rose-200">
          <p className="text-rose-700 font-semibold">{error}</p>
        </article>
      )}

      {!loading && !error && data && (
        <>
          <article className="surface-card rounded-3xl p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500 font-semibold">Profile</p>
                <h3 className="text-2xl font-bold text-slate-900 mt-1">{data.profile.name}</h3>
                <p className="text-sm text-slate-600 mt-1">
                  Section {data.profile.section} | CGPA {data.profile.cgpa} | Backlogs {data.profile.backlogs}
                </p>
              </div>
              <span
                className={`text-xs border rounded-full px-3 py-1.5 font-semibold ${statusTone(data.profile.readiness_status)}`}
              >
                {data.profile.readiness_status} ({data.profile.readiness_score})
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-5">
              <div className="bg-slate-50 rounded-2xl border border-slate-200 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500 font-semibold">Skills</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {data.profile.skills.map((skill) => (
                    <span key={skill} className="text-xs px-2.5 py-1 rounded-full border border-slate-300 bg-white text-slate-700">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
              <div className="bg-teal-50 rounded-2xl border border-teal-200 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-teal-700 font-semibold">AI-Verified Skills</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {data.profile.verified_skills.length === 0 ? (
                    <span className="text-xs text-teal-700">No verified skills yet.</span>
                  ) : (
                    data.profile.verified_skills.map((skill) => (
                      <span
                        key={skill}
                        className="text-xs px-2.5 py-1 rounded-full border border-teal-200 bg-white text-teal-700 font-semibold"
                      >
                        AI-Verified {skill}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </article>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            <article className="surface-card rounded-3xl p-6 xl:col-span-7">
              <h3 className="text-xl font-bold text-slate-900">Company Recommendations</h3>
              <div className="mt-4 space-y-3 max-h-[420px] overflow-y-auto pr-1">
                {data.recommendations.length === 0 ? (
                  <p className="text-sm text-slate-500">No recommendation decisions yet.</p>
                ) : (
                  data.recommendations.map((item, index) => (
                    <article key={`${item.company}-${item.role}-${index}`} className="bg-white border border-slate-200 rounded-2xl p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-slate-900">{item.company}</p>
                          <p className="text-xs text-slate-500">{item.role}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs px-2 py-1 rounded-full border border-blue-200 bg-blue-50 text-blue-700 font-semibold">
                            Match {item.match_score}%
                          </span>
                          <span className="text-xs px-2 py-1 rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700 font-semibold">
                            Select {item.selection_probability}%
                          </span>
                          <span
                            className={`text-xs px-2 py-1 rounded-full border font-semibold ${recommendationTone(item.status)}`}
                          >
                            {item.status}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-slate-600 mt-3">{item.reasoning}</p>
                      <p className="text-sm text-emerald-700 mt-2">
                        <span className="font-semibold">Action:</span> {item.autonomous_action}
                      </p>
                    </article>
                  ))
                )}
              </div>
            </article>

            <article className="surface-card rounded-3xl p-6 xl:col-span-5">
              <h3 className="text-xl font-bold text-slate-900">Interventions</h3>
              <div className="mt-4 space-y-3 max-h-[420px] overflow-y-auto pr-1">
                {data.interventions.length === 0 ? (
                  <p className="text-sm text-slate-500">No interventions assigned.</p>
                ) : (
                  data.interventions.map((item, index) => (
                    <article key={`${item.intervention_type}-${index}`} className="bg-white border border-slate-200 rounded-2xl p-4">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900">{item.intervention_type}</p>
                        <span className="text-xs px-2 py-1 rounded-full border border-slate-300 bg-slate-50 text-slate-700">
                          {item.status}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 mt-2">{item.details}</p>
                      <p className="text-xs text-slate-500 mt-2">{item.created_at}</p>
                    </article>
                  ))
                )}
              </div>
            </article>
          </div>

          <article className="surface-card rounded-3xl p-6">
            <h3 className="text-xl font-bold text-slate-900">Autonomous Upskiller Quizzes</h3>
            <p className="text-sm text-slate-600 mt-1">
              Zero-click quizzes generated by the agent when Python risk is detected.
            </p>
            <div className="mt-4 space-y-3">
              {(data.autonomous_quizzes || []).length === 0 ? (
                <p className="text-sm text-slate-500">No autonomous quiz assigned yet.</p>
              ) : (
                (data.autonomous_quizzes || []).map((quiz) => (
                  <article key={quiz.token} className="bg-white border border-slate-200 rounded-2xl p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">{quiz.company}</p>
                        <p className="text-xs text-slate-500">{quiz.role} | {quiz.topic}</p>
                      </div>
                      <span className="text-xs px-2 py-1 rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700 font-semibold">
                        {quiz.delivery_status}
                      </span>
                    </div>
                    <a
                      href={`/quiz/${quiz.token}`}
                      className="inline-block mt-3 text-sm font-semibold text-teal-700 hover:text-teal-800"
                    >
                      Open Quiz Link
                    </a>
                    <div className="mt-3 space-y-2">
                      {quiz.questions.map((q, idx) => (
                        <div key={`${quiz.token}-${idx}`} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                          <p className="text-sm font-semibold text-slate-800">
                            Q{idx + 1}. {q.question}
                          </p>
                          <p className="text-xs text-slate-500 mt-1">Difficulty: {q.difficulty}</p>
                          <p className="text-xs text-slate-600 mt-1">Hint: {q.starter_hint}</p>
                        </div>
                      ))}
                    </div>
                  </article>
                ))
              )}
            </div>
          </article>

          <article className="surface-card rounded-3xl p-6">
            <h3 className="text-xl font-bold text-slate-900">Journey Timeline</h3>
            <div className="mt-4 space-y-3">
              {data.journey_events.length === 0 ? (
                <p className="text-sm text-slate-500">No timeline events found.</p>
              ) : (
                data.journey_events.map((event, index) => (
                  <article key={`${event.event_type}-${index}`} className="bg-white border border-slate-200 rounded-2xl p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-900">{event.event_type}</p>
                      <p className="text-xs text-slate-500">{event.event_time}</p>
                    </div>
                    <pre className="text-xs text-slate-600 mt-2 whitespace-pre-wrap break-words">
                      {JSON.stringify(event.payload, null, 2)}
                    </pre>
                  </article>
                ))
              )}
            </div>
          </article>
        </>
      )}
    </section>
  );
}
