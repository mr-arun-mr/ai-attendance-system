import { useEffect, useState } from "react";
import { format, subDays } from "date-fns";
import { getWeeklyReport, getDailySummary, exportCSV, getDepartments } from "../api";
import StatCard from "../components/StatCard";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

interface WeekRow { date: string; present: number; late: number }
interface Dept { id: number; name: string }

export default function Reports() {
  const [weekly, setWeekly] = useState<WeekRow[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [departments, setDepartments] = useState<Dept[]>([]);
  const [exportStart, setExportStart] = useState(format(subDays(new Date(), 29), "yyyy-MM-dd"));
  const [exportEnd, setExportEnd] = useState(format(new Date(), "yyyy-MM-dd"));
  const [exportDept, setExportDept] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    getWeeklyReport().then(setWeekly).catch(console.error);
    getDailySummary().then(setSummary).catch(console.error);
    getDepartments().then(setDepartments).catch(console.error);
  }, []);

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

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-sm text-gray-500 mt-1">Attendance analytics and exports</p>
      </div>

      {/* Today summary */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Registered" value={summary.total_registered} color="blue" />
          <StatCard label="Present Today" value={summary.present} color="green" />
          <StatCard label="Absent Today" value={summary.absent} color="red" />
          <StatCard label="Late Today" value={summary.late} color="yellow" />
        </div>
      )}

      {/* Weekly chart */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
        <h2 className="text-base font-semibold mb-4">Last 7 Days</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={weekly} margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => format(new Date(v), "EEE d")}
              tick={{ fontSize: 12 }}
            />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              labelFormatter={(v) => format(new Date(v as string), "EEE, MMM d")}
            />
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
      </div>
    </div>
  );
}
