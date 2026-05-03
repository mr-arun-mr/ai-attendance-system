import { useEffect, useState } from "react";
import { getDailySummary, getAttendance } from "../api";
import StatCard from "../components/StatCard";
import { format } from "date-fns";

interface Summary {
  date: string;
  total_registered: number;
  present: number;
  absent: number;
  late: number;
}

interface AttendanceRecord {
  id: number;
  full_name: string;
  employee_id: string;
  department: string | null;
  check_in: string;
  is_late: boolean;
  source: string;
}

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<AttendanceRecord[]>([]);

  useEffect(() => {
    getDailySummary().then(setSummary).catch(console.error);
    getAttendance({ date: format(new Date(), "yyyy-MM-dd"), limit: 10 })
      .then(setRecent)
      .catch(console.error);
  }, []);

  const pct = summary
    ? Math.round((summary.present / Math.max(summary.total_registered, 1)) * 100)
    : 0;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          {format(new Date(), "EEEE, MMMM d, yyyy")}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Registered"
          value={summary?.total_registered ?? "—"}
          color="blue"
        />
        <StatCard
          label="Present Today"
          value={summary?.present ?? "—"}
          sub={`${pct}% attendance rate`}
          color="green"
        />
        <StatCard
          label="Absent"
          value={summary?.absent ?? "—"}
          color="red"
        />
        <StatCard
          label="Late Arrivals"
          value={summary?.late ?? "—"}
          color="yellow"
        />
      </div>

      {/* Recent check-ins */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-base font-semibold mb-4">Recent Check-ins Today</h2>
        {recent.length === 0 ? (
          <p className="text-sm text-gray-400">No check-ins yet today.</p>
        ) : (
          <div className="space-y-3">
            {recent.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium">{r.full_name}</p>
                  <p className="text-xs text-gray-400">
                    {r.employee_id}
                    {r.department ? ` · ${r.department}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">
                    {format(new Date(r.check_in), "HH:mm")}
                  </p>
                  <p className="text-xs text-gray-400">
                    {r.is_late ? (
                      <span className="text-yellow-600">Late</span>
                    ) : (
                      <span className="text-green-600">On time</span>
                    )}{" "}
                    · {r.source}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
