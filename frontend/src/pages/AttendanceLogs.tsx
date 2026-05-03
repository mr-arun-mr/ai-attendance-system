import { useEffect, useState } from "react";
import { format } from "date-fns";
import {
  getAttendance, getDepartments, createManualAttendance,
  updateAttendance, deleteAttendance,
} from "../api";
import Badge from "../components/Badge";
import Modal from "../components/Modal";
import { useAuth } from "../context/AuthContext";

interface Log {
  id: number;
  user_id: number;
  full_name: string;
  employee_id: string;
  department: string | null;
  check_in: string;
  check_out: string | null;
  date: string;
  confidence: number | null;
  source: string;
  is_late: boolean;
}

interface Dept { id: number; name: string }

export default function AttendanceLogs() {
  const { user: authUser } = useAuth();
  const [logs, setLogs] = useState<Log[]>([]);
  const [departments, setDepartments] = useState<Dept[]>([]);
  const [filterDate, setFilterDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [filterDept, setFilterDept] = useState("");
  const [editLog, setEditLog] = useState<Log | null>(null);
  const [showManual, setShowManual] = useState(false);
  const [manualForm, setManualForm] = useState({ user_id: "", check_in: "", date: "" });
  const [loading, setLoading] = useState(false);

  const load = () => {
    const params: Record<string, unknown> = {};
    if (filterDate) params.date = filterDate;
    if (filterDept) params.department_id = filterDept;
    getAttendance(params).then(setLogs).catch(console.error);
  };

  useEffect(() => {
    getDepartments().then(setDepartments).catch(console.error);
  }, []);

  useEffect(load, [filterDate, filterDept]);

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this record?")) return;
    await deleteAttendance(id);
    load();
  };

  const handleCheckout = async (log: Log) => {
    await updateAttendance(log.id, {
      check_out: new Date().toISOString(),
    });
    load();
  };

  const handleManual = async () => {
    setLoading(true);
    try {
      await createManualAttendance({
        user_id: Number(manualForm.user_id),
        check_in: new Date(manualForm.check_in).toISOString(),
        date: manualForm.date || undefined,
      });
      setShowManual(false);
      load();
    } catch (e: any) {
      alert(e.response?.data?.detail ?? "Error creating record");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Attendance Logs</h1>
          <p className="text-sm text-gray-500 mt-1">View and manage attendance records</p>
        </div>
        {authUser?.is_admin && (
          <button
            onClick={() => setShowManual(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            + Manual Entry
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
          <input
            type="date"
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Department</label>
          <select
            value={filterDept}
            onChange={(e) => setFilterDept(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Name", "ID", "Dept", "Check In", "Check Out", "Status", "Source", "Actions"].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{log.full_name}</td>
                <td className="px-4 py-3 text-gray-500">{log.employee_id}</td>
                <td className="px-4 py-3 text-gray-500">{log.department ?? "—"}</td>
                <td className="px-4 py-3">{format(new Date(log.check_in), "HH:mm")}</td>
                <td className="px-4 py-3">
                  {log.check_out ? format(new Date(log.check_out), "HH:mm") : "—"}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={log.is_late ? "Late" : "On time"}
                    color={log.is_late ? "yellow" : "green"}
                  />
                </td>
                <td className="px-4 py-3 text-gray-500 capitalize">{log.source}</td>
                <td className="px-4 py-3">
                  {authUser?.is_admin && (
                    <div className="flex gap-2">
                      {!log.check_out && (
                        <button
                          onClick={() => handleCheckout(log)}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Check out
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(log.id)}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && (
          <p className="text-center text-sm text-gray-400 py-10">No records found.</p>
        )}
      </div>

      {/* Manual entry modal */}
      {showManual && (
        <Modal title="Manual Attendance Entry" onClose={() => setShowManual(false)}>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">User ID</label>
              <input
                type="number"
                value={manualForm.user_id}
                onChange={(e) => setManualForm((f) => ({ ...f, user_id: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Enter user ID"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Check-in Time</label>
              <input
                type="datetime-local"
                value={manualForm.check_in}
                onChange={(e) => setManualForm((f) => ({ ...f, check_in: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Date (optional)</label>
              <input
                type="date"
                value={manualForm.date}
                onChange={(e) => setManualForm((f) => ({ ...f, date: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleManual}
                disabled={loading}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
              >
                {loading ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => setShowManual(false)}
                className="flex-1 border border-gray-300 py-2 rounded-lg text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
