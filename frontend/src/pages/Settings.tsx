import { useEffect, useState } from "react";
import {
  getCameras, createCamera, updateCamera, deleteCamera,
  getDepartments, createDepartment, deleteDepartment,
} from "../api";
import Modal from "../components/Modal";
import Badge from "../components/Badge";
import { useAuth } from "../context/AuthContext";

interface Camera { id: number; name: string; location: string | null; stream_url: string; is_active: boolean }
interface Dept { id: number; name: string }

export default function Settings() {
  const { user } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [departments, setDepartments] = useState<Dept[]>([]);
  const [showAddCam, setShowAddCam] = useState(false);
  const [camForm, setCamForm] = useState({ name: "", location: "", stream_url: "", is_active: true });
  const [editCam, setEditCam] = useState<Camera | null>(null);
  const [newDept, setNewDept] = useState("");
  const [saving, setSaving] = useState(false);

  const loadCams = () => getCameras().then(setCameras).catch(console.error);
  const loadDepts = () => getDepartments().then(setDepartments).catch(console.error);

  useEffect(() => {
    loadCams();
    loadDepts();
  }, []);

  const handleSaveCam = async () => {
    setSaving(true);
    try {
      const payload = { ...camForm, location: camForm.location || null };
      if (editCam) {
        await updateCamera(editCam.id, payload);
      } else {
        await createCamera(payload);
      }
      setShowAddCam(false);
      setEditCam(null);
      setCamForm({ name: "", location: "", stream_url: "", is_active: true });
      loadCams();
    } catch (e: any) {
      alert(e.response?.data?.detail ?? "Error saving camera");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCam = async (id: number) => {
    if (!confirm("Delete this camera?")) return;
    await deleteCamera(id);
    loadCams();
  };

  const handleAddDept = async () => {
    if (!newDept.trim()) return;
    await createDepartment(newDept.trim());
    setNewDept("");
    loadDepts();
  };

  const handleDeleteDept = async (id: number) => {
    if (!confirm("Delete this department?")) return;
    await deleteDepartment(id);
    loadDepts();
  };

  if (!user?.is_admin) {
    return (
      <div className="p-8 text-gray-500 text-sm">Admin access required.</div>
    );
  }

  return (
    <div className="p-8 space-y-8 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Camera and department configuration</p>
      </div>

      {/* Cameras */}
      <section className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">Cameras</h2>
          <button
            onClick={() => { setShowAddCam(true); setEditCam(null); setCamForm({ name: "", location: "", stream_url: "", is_active: true }); }}
            className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-blue-700"
          >
            + Add Camera
          </button>
        </div>
        <div className="space-y-3">
          {cameras.map((c) => (
            <div key={c.id} className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
              <div>
                <p className="text-sm font-medium">{c.name}</p>
                <p className="text-xs text-gray-500">{c.location ? `${c.location} · ` : ""}{c.stream_url}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge label={c.is_active ? "Active" : "Inactive"} color={c.is_active ? "green" : "gray"} />
                <button
                  onClick={() => { setEditCam(c); setCamForm({ name: c.name, location: c.location ?? "", stream_url: c.stream_url, is_active: c.is_active }); setShowAddCam(true); }}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteCam(c.id)}
                  className="text-xs text-red-600 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          {cameras.length === 0 && <p className="text-sm text-gray-400">No cameras configured.</p>}
        </div>
      </section>

      {/* Departments */}
      <section className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="text-base font-semibold mb-4">Departments</h2>
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newDept}
            onChange={(e) => setNewDept(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddDept()}
            placeholder="New department name…"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={handleAddDept}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Add
          </button>
        </div>
        <div className="space-y-2">
          {departments.map((d) => (
            <div key={d.id} className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
              <p className="text-sm">{d.name}</p>
              <button
                onClick={() => handleDeleteDept(d.id)}
                className="text-xs text-red-600 hover:underline"
              >
                Delete
              </button>
            </div>
          ))}
          {departments.length === 0 && <p className="text-sm text-gray-400">No departments.</p>}
        </div>
      </section>

      {/* Camera modal */}
      {showAddCam && (
        <Modal title={editCam ? "Edit Camera" : "Add Camera"} onClose={() => setShowAddCam(false)}>
          <div className="space-y-3">
            {(["name", "location", "stream_url"] as const).map((field) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                  {field.replace("_", " ")}
                  {field === "location" ? " (optional)" : ""}
                </label>
                <input
                  type="text"
                  value={camForm[field]}
                  onChange={(e) => setCamForm((f) => ({ ...f, [field]: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder={field === "stream_url" ? "rtsp://... or http://..." : ""}
                />
              </div>
            ))}
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={camForm.is_active}
                onChange={(e) => setCamForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              Active
            </label>
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleSaveCam}
                disabled={saving}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button onClick={() => setShowAddCam(false)} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">
                Cancel
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
