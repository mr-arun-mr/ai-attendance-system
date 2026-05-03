import { useEffect, useState, useRef } from "react";
import {
  getUsers, createUser, updateUser, deleteUser,
  getDepartments, registerFaces, deleteFace,
} from "../api";
import Modal from "../components/Modal";
import Badge from "../components/Badge";
import { useAuth } from "../context/AuthContext";

interface User {
  id: number;
  full_name: string;
  email: string;
  employee_id: string;
  is_active: boolean;
  is_admin: boolean;
  department_id: number | null;
  has_face: boolean;
}

interface Department {
  id: number;
  name: string;
}

const EMPTY_FORM = {
  full_name: "", email: "", employee_id: "", password: "",
  department_id: "" as string | number, is_admin: false,
};

export default function People() {
  const { user: authUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [faceTarget, setFaceTarget] = useState<User | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [capturedFiles, setCapturedFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  const load = () => {
    getUsers().then(setUsers).catch(console.error);
    getDepartments().then(setDepartments).catch(console.error);
  };

  useEffect(load, []);

  const filtered = users.filter(
    (u) =>
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.employee_id.toLowerCase().includes(search.toLowerCase())
  );

  const handleSave = async () => {
    setLoading(true);
    try {
      const payload = {
        ...form,
        department_id: form.department_id ? Number(form.department_id) : null,
      };
      if (editUser) {
        await updateUser(editUser.id, payload);
      } else {
        await createUser(payload);
      }
      setShowAdd(false);
      setEditUser(null);
      setForm({ ...EMPTY_FORM });
      load();
    } catch (e: any) {
      alert(e.response?.data?.detail ?? "Error saving user");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (u: User) => {
    if (!confirm(`Delete ${u.full_name}?`)) return;
    await deleteUser(u.id);
    load();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []).slice(0, 10);
    setCapturedFiles(files);
    setPreviews(files.map((f) => URL.createObjectURL(f)));
  };

  const handleRegisterFace = async () => {
    if (!faceTarget || capturedFiles.length === 0) return;
    setLoading(true);
    try {
      await registerFaces(faceTarget.id, capturedFiles);
      alert("Face registered successfully!");
      setFaceTarget(null);
      setCapturedFiles([]);
      setPreviews([]);
      load();
    } catch (e: any) {
      alert(e.response?.data?.detail ?? "Face registration failed");
    } finally {
      setLoading(false);
    }
  };

  const openEdit = (u: User) => {
    setEditUser(u);
    setForm({
      full_name: u.full_name, email: u.email, employee_id: u.employee_id,
      password: "", department_id: u.department_id ?? "", is_admin: u.is_admin,
    });
    setShowAdd(true);
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">People</h1>
          <p className="text-sm text-gray-500 mt-1">Manage employees and face registrations</p>
        </div>
        {authUser?.is_admin && (
          <button
            onClick={() => { setShowAdd(true); setEditUser(null); setForm({ ...EMPTY_FORM }); }}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            + Add Person
          </button>
        )}
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search by name or ID…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full max-w-sm border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-blue-500 focus:outline-none"
      />

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Name", "Employee ID", "Department", "Face", "Status", "Actions"].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filtered.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium">{u.full_name}</td>
                <td className="px-4 py-3 text-gray-500">{u.employee_id}</td>
                <td className="px-4 py-3 text-gray-500">
                  {departments.find((d) => d.id === u.department_id)?.name ?? "—"}
                </td>
                <td className="px-4 py-3">
                  <Badge label={u.has_face ? "Registered" : "Not set"} color={u.has_face ? "green" : "gray"} />
                </td>
                <td className="px-4 py-3">
                  <Badge label={u.is_active ? "Active" : "Inactive"} color={u.is_active ? "blue" : "red"} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {authUser?.is_admin && (
                      <>
                        <button
                          onClick={() => openEdit(u)}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => { setFaceTarget(u); setCapturedFiles([]); setPreviews([]); }}
                          className="text-xs text-green-600 hover:underline"
                        >
                          Face
                        </button>
                        <button
                          onClick={() => handleDelete(u)}
                          className="text-xs text-red-600 hover:underline"
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="text-center text-gray-400 text-sm py-10">No people found.</p>
        )}
      </div>

      {/* Add / Edit modal */}
      {showAdd && (
        <Modal
          title={editUser ? "Edit Person" : "Add Person"}
          onClose={() => { setShowAdd(false); setEditUser(null); }}
        >
          <div className="space-y-3">
            {["full_name", "email", "employee_id"].map((field) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                  {field.replace("_", " ")}
                </label>
                <input
                  type={field === "email" ? "email" : "text"}
                  value={(form as any)[field]}
                  onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            ))}
            {!editUser && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Password</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Department</label>
              <select
                value={form.department_id}
                onChange={(e) => setForm((f) => ({ ...f, department_id: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">None</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_admin}
                onChange={(e) => setForm((f) => ({ ...f, is_admin: e.target.checked }))}
              />
              Admin role
            </label>
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleSave}
                disabled={loading}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
              >
                {loading ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => { setShowAdd(false); setEditUser(null); }}
                className="flex-1 border border-gray-300 py-2 rounded-lg text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Face registration modal */}
      {faceTarget && (
        <Modal
          title={`Register Face — ${faceTarget.full_name}`}
          onClose={() => setFaceTarget(null)}
          wide
        >
          <p className="text-sm text-gray-500 mb-4">
            Upload 3–10 clear face photos. The system will average the embeddings for best accuracy.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileRef.current?.click()}
            className="w-full border-2 border-dashed border-gray-300 rounded-xl py-8 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors mb-4"
          >
            Click to select photos (max 10)
          </button>
          {previews.length > 0 && (
            <div className="grid grid-cols-5 gap-2 mb-4">
              {previews.map((src, i) => (
                <img key={i} src={src} className="w-full aspect-square object-cover rounded-lg" />
              ))}
            </div>
          )}
          <div className="flex gap-3">
            <button
              onClick={handleRegisterFace}
              disabled={loading || capturedFiles.length === 0}
              className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60"
            >
              {loading ? "Registering…" : `Register (${capturedFiles.length} photo${capturedFiles.length !== 1 ? "s" : ""})`}
            </button>
            {faceTarget.has_face && (
              <button
                onClick={async () => {
                  await deleteFace(faceTarget.id);
                  setFaceTarget(null);
                  load();
                }}
                className="px-4 py-2 rounded-lg text-sm border border-red-300 text-red-600 hover:bg-red-50"
              >
                Remove face
              </button>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
