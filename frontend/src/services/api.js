const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiService = {
  fetchDashboardData: async () => {
    const response = await fetch(`${API_BASE_URL}/api/dashboard/live-insights`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed with status ${response.status}`);
    }

    const payload = await response.json();

    if (payload.status !== "success" || !payload.data) {
      throw new Error("Invalid backend response contract");
    }

    return payload.data;
  },
};

export default apiService;
