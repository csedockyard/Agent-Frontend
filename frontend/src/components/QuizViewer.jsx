import { useEffect, useState } from "react";

import apiService from "../services/api";

export default function QuizViewer({ quizToken }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [quiz, setQuiz] = useState(null);

  useEffect(() => {
    const loadQuiz = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await apiService.fetchQuizDetail(quizToken);
        setQuiz(response);
      } catch (fetchError) {
        console.error("Failed to load quiz:", fetchError);
        setError(fetchError.message || "Quiz not found.");
      } finally {
        setLoading(false);
      }
    };

    loadQuiz();
  }, [quizToken]);

  if (loading) {
    return (
      <div className="app-shell min-h-screen flex items-center justify-center p-6">
        <article className="surface-card rounded-3xl px-8 py-10">
          <p className="text-slate-700 font-semibold">Loading autonomous quiz...</p>
        </article>
      </div>
    );
  }

  if (error || !quiz) {
    return (
      <div className="app-shell min-h-screen flex items-center justify-center p-6">
        <article className="surface-card rounded-3xl px-8 py-10 border border-rose-200 text-center">
          <p className="text-rose-700 font-semibold">{error || "Quiz unavailable."}</p>
          <a href="/" className="inline-block mt-4 text-sm font-semibold text-teal-700">
            Back to Dashboard
          </a>
        </article>
      </div>
    );
  }

  return (
    <div className="app-shell min-h-screen p-4 md:p-7 xl:p-10 text-slate-900">
      <div className="max-w-4xl mx-auto space-y-5">
        <article className="surface-card rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500 font-semibold">
            Autonomous Upskiller
          </p>
          <h1 className="text-3xl font-bold text-slate-900 mt-2">{quiz.company} Python Challenge</h1>
          <p className="text-sm text-slate-600 mt-2">
            Role: {quiz.role} | Delivery: {quiz.delivery_status}
          </p>
        </article>

        <section className="space-y-4">
          {quiz.questions.map((question, index) => (
            <article key={`${quiz.token}-${index}`} className="surface-card rounded-3xl p-6">
              <p className="text-sm font-semibold text-slate-800">Question {index + 1}</p>
              <p className="text-lg font-semibold text-slate-900 mt-2">{question.question}</p>
              <p className="text-xs text-slate-500 mt-2">Difficulty: {question.difficulty}</p>
              <p className="text-xs text-slate-500 mt-1">
                Topics: {question.expected_topics.join(", ")}
              </p>
              <p className="text-sm text-teal-700 mt-2">Hint: {question.starter_hint}</p>
              <textarea
                className="mt-4 w-full rounded-2xl border border-slate-300 bg-white p-3 text-sm min-h-[110px]"
                placeholder="Write your answer / approach here..."
              />
            </article>
          ))}
        </section>

        <article className="surface-card rounded-3xl p-6 text-center">
          <p className="text-sm text-slate-600">
            This prototype tracks completion via generated quizzes and intervention logs.
          </p>
          <a href="/" className="inline-block mt-3 text-sm font-semibold text-teal-700">
            Back to Dashboard
          </a>
        </article>
      </div>
    </div>
  );
}
