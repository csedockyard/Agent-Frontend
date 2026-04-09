import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
);

const AnalyticsCharts = ({ activeCampaign }) => {
  const eligibility = activeCampaign.eligibility_enforced;

  const barData = {
    labels: ["Total Scanned", "Eligible Unlocked", "Ineligible Blocked"],
    datasets: [
      {
        label: "Students",
        data: [
          eligibility.total_scanned,
          eligibility.eligible_unlocked,
          eligibility.ineligible_blocked,
        ],
        backgroundColor: ["#475569", "#0f766e", "#e11d48"],
        borderRadius: 10,
        borderSkipped: false,
      },
    ],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#0f172a",
        titleColor: "#e2e8f0",
        bodyColor: "#f8fafc",
        padding: 10,
        cornerRadius: 8,
        callbacks: {
          label: (context) => `${context.parsed.y} students`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: "rgba(148,163,184,0.25)" },
        ticks: { color: "#475569" },
      },
      x: {
        grid: { display: false },
        ticks: { color: "#334155" },
      },
    },
  };

  const doughnutData = {
    labels: ["Eligible", "Blocked"],
    datasets: [
      {
        data: [eligibility.eligible_unlocked, eligibility.ineligible_blocked],
        backgroundColor: ["#0f766e", "#e11d48"],
        borderWidth: 2,
        borderColor: "#ffffff",
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "65%",
    plugins: {
      legend: {
        position: "right",
        labels: { boxWidth: 12, color: "#334155", font: { family: "Manrope, sans-serif", size: 11 } },
      },
    },
  };

  return (
    <section className="surface-card rounded-3xl p-6 flex-1 flex flex-col min-h-[420px] xl:min-h-[350px]">
      <h2 className="text-xl font-bold text-slate-900 mb-1">Campaign Analytics</h2>
      <p className="text-xs text-slate-500 mb-4">Distribution of autonomous eligibility outcomes.</p>

      <div className="grid grid-rows-2 gap-4 flex-1 h-full min-h-0">
        <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 flex flex-col h-full">
          <h3 className="text-sm font-semibold text-slate-700 mb-2 text-center">Screening Volume</h3>
          <div className="relative w-full mx-auto flex-1 h-[200px]">
            <Bar data={barData} options={barOptions} />
          </div>
        </div>

        <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 flex flex-col h-full">
          <h3 className="text-sm font-semibold text-slate-700 mb-2 text-center">Eligibility Split</h3>
          <div className="relative w-full mx-auto flex-1 h-[200px]">
            <Doughnut data={doughnutData} options={doughnutOptions} />
          </div>
        </div>
      </div>
    </section>
  );
};

export default AnalyticsCharts;
