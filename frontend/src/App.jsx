import Dashboard from "./components/Dashboard";
import QuizViewer from "./components/QuizViewer";

function App() {
  const path = window.location.pathname;
  if (path.startsWith("/quiz/")) {
    const token = path.split("/quiz/")[1];
    if (token) {
      return <QuizViewer quizToken={token} />;
    }
  }
  return <Dashboard />;
}

export default App;
