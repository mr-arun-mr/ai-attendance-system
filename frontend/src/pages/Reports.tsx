import { useEffect, useState } from "react";
import { format, subDays } from "date-fns";
import {
  getWeeklyReport, getDailySummary, exportCSV,
  getDepartments, getUserTimeSummary,
} from "../api";
import StatCard from "../components/StatCard";
import Badge from "../components/Badge";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

interface WeekRow { date: string; present: number; late: number }
interface Dept { id: number; name: string }
interface UserTime {
  user_id: number;
  full_name: string;
  employee_id: string;
  department: string | null;
  check_in: string | null;
  check_out: string | null;
  duration_minutes: number | null;
  is_late: boolean;
}
interface Summary {
  date: string;
  total_registered: number;
  present: number;
  absent: number;
  late: number;
  avg_duration_minutes: number | null;
}

function fmtDuration(minutes: number | null): string {
  if (minutes == null) return "—";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return format(new Date(iso), "HH:mm");
}

export default function Reports() {
  const [weekly, setWeekly] = useState<WeekRow[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [departments, setDepartments] = useState<Dept[]>([]);
  const [userTimes, setUserTimes] = useState<UserTime[]>([]);
  const [summaryDate, setSummaryDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [summaryDept, setSummaryDept] = useState("");
  const [exportStart, setExportStart] = useState(format(subDays(new Date(), 29), "yyyy-MM-dd"));
  const [exportEnd, setExportEnd] = useState(format(new Date(), "yyyy-MM-dd"));
  const [exportDept, setExportDept] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    getWeeklyReport().then(setWeekly).catch(console.error);
    getDepartments().then(setDepartments).catch(console.error);
  }, []);

  useEffect(() => {
    const params: Record<string, unknown> = { date: summaryDate };
    if (summaryDept) params.department_id = summaryDept;
    getDailySummary(summaryDate).then(setSummary).catch(console.error);
    getUserTimeSummary(params).then(setUserTimes).catch(console.error);
  }, [summaryDate, summaryDept]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await exportCSV({
        start_date: exportStart,
        end_date: exportEnd,
        department_id: exportDept || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `attendance_${exportStart}_${exportEnd}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const totalDuration = userTimes.reduce((s, u) => s + (u.duration_minutes ?? 0), 0);
  const completedCount = userTimes.filter((u) => u.duration_minutes != null).length;

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-sm text-gray-500 mt-1">Attendance analytics, time tracking, and exports</p>
      </div>

      {/* Date + dept filter for summary section */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
          <input
            type="date"
            value={summaryDate}
            onChange={(e) => setSummaryDate(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Department</label>
          <select
            value={summaryDept}
            onChange={(e) => setSummaryDept(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary stat cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard label="Total Registered" value={summary.total_registered} color="blue" />
          <StatCard label="Present" value={summary.present} color="green" />
          <StatCard label="Absent" value={summary.absent} color="red" />
          <StatCard label="Late" value={summary.late} color="yellow" />
          <StatCard
            label="Avg Time In"
            value={fmtDuration(summary.avg_duration_minutes)}
            sub="checked-out records only"
            color="blue"
          />
        </div>
      )}

      {/* Daily Time Summary table */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-base font-semibold">Daily Time Summary</h2>
          {completedCount > 0 && (
            <span className="text-xs text-gray-500">
              Total hours tracked: {fmtDuration(totalDuration)} across {completedCount} person{completedCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {["Name", "ID", "Department", "Check In", "Check Out", "Time In", "Status"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {userTimes.map((u) => (
                <tr key={u.user_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{u.full_name}</td>
                  <td className="px-4 py-3 text-gray-500">{u.employee_id}</td>
                  <td className="px-4 py-3 text-gray-500">{u.department ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-sm">{fmtTime(u.check_in)}</td>
                  <td className="px-4 py-3 font-mono text-sm">
                    {u.check_out ? (
                      fmtTime(u.check_out)
                    ) : (
                      <span className="text-yellow-600 text-xs">Still in</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {u.duration_minutes != null ? (
                      <span className="font-semibold text-blue-700">
                        {fmtDuration(u.duration_minutes)}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">In progress</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      label={u.is_late ? "Late" : "On time"}
                      color={u.is_late ? "yellow" : "green"}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {userTimes.length === 0 && (
            <p className="text-center text-sm text-gray-400 py-10">
              No attendance records for this date.
            </p>
          )}
        </div>
      </div>

      {/* Weekly trend chart */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="text-base font-semibold mb-4">Last 7 Days — Attendance Trend</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={weekly} margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => format(new Date(v), "EEE d")}
              tick={{ fontSize: 12 }}
            />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip labelFormatter={(v) => format(new Date(v as string), "EEE, MMM d")} />
            <Legend />
            <Bar dataKey="present" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Present" />
            <Bar dataKey="late" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Late" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* CSV Export */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="text-base font-semibold mb-4">Export to CSV</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Start Date</label>
            <input
              type="date"
              value={exportStart}
              onChange={(e) => setExportStart(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
            <input
              type="date"
              value={exportEnd}
              onChange={(e) => setExportEnd(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Department</label>
            <select
              value={exportDept}
              onChange={(e) => setExportDept(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60"
          >
            {exporting ? "Exporting…" : "Download CSV"}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-3">
          CSV includes: date, employee ID, name, department, check-in, check-out, duration, late status, source, confidence
        </p>
      </div>
    </div>
  );
}
