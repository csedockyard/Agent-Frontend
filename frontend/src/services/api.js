const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://localhost:8000" : "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = payload?.detail || `Failed with status ${response.status}`;
    throw new Error(detail);
  }

  return payload;
}

const apiService = {
  fetchDashboardData: async () => {
    const payload = await request("/api/dashboard/live-insights", { method: "GET" });
    if (payload.status !== "success" || !payload.data) {
      throw new Error("Invalid live insights response contract");
    }
    return payload.data;
  },

  fetchAdminAnalytics: async () => {
    const payload = await request("/api/admin/analytics", { method: "GET" });
    if (payload.status !== "success" || !payload.data) {
      throw new Error("Invalid admin analytics response contract");
    }
    return payload.data;
  },

  fetchStudentJourney: async (studentId) => {
    const payload = await request(`/api/students/${studentId}/journey`, { method: "GET" });
    if (payload.status !== "success" || !payload.data) {
      throw new Error("Invalid student journey response contract");
    }
    return payload.data;
  },

  triggerAgentCycle: async () => {
    const payload = await request("/api/agents/run-cycle", { method: "POST" });
    if (payload.status !== "success") {
      throw new Error("Failed to run agent cycle");
    }
    return payload;
  },

  applySimulationAction: async ({ student_id, action_type, value = null, metadata = {} }) => {
    const payload = await request("/api/simulations/apply-action", {
      method: "POST",
      body: JSON.stringify({ student_id, action_type, value, metadata }),
    });
    if (payload.status !== "success" || !payload.result) {
      throw new Error("Simulation action failed");
    }
    return payload.result;
  },

  runWhatIfTrajectory: async ({ student_id, prompt }) => {
    const payload = await request("/api/simulations/what-if", {
      method: "POST",
      body: JSON.stringify({ student_id, prompt }),
    });
    if (payload.status !== "success" || !payload.data) {
      throw new Error("What-if simulation failed");
    }
    return payload.data;
  },

  runDemoOneClick: async () => {
    const payload = await request("/api/demo/one-click", { method: "POST" });
    if (payload.status !== "success" || !payload.data) {
      throw new Error("Demo mode failed");
    }
    return payload.data;
  },

  fetchQuizDetail: async (quizToken) => {
    const payload = await request(`/api/quizzes/${quizToken}`, { method: "GET" });
    if (payload.status !== "success" || !payload.data) {
      throw new Error("Quiz detail fetch failed");
    }
    return payload.data;
  },
};

export default apiService;
