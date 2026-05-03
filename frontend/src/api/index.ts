import api from "./client";

// Auth
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);

// Users
export const getUsers = (params?: Record<string, unknown>) =>
  api.get("/users/", { params }).then((r) => r.data);

export const createUser = (data: Record<string, unknown>) =>
  api.post("/users/", data).then((r) => r.data);

export const updateUser = (id: number, data: Record<string, unknown>) =>
  api.patch(`/users/${id}`, data).then((r) => r.data);

export const deleteUser = (id: number) => api.delete(`/users/${id}`);

export const uploadUserPhoto = (id: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post(`/users/${id}/photo`, form).then((r) => r.data);
};

// Departments
export const getDepartments = () =>
  api.get("/departments/").then((r) => r.data);

export const createDepartment = (name: string) =>
  api.post("/departments/", { name }).then((r) => r.data);

export const deleteDepartment = (id: number) =>
  api.delete(`/departments/${id}`);

// Faces
export const registerFaces = (userId: number, files: File[]) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return api.post(`/faces/register/${userId}`, form).then((r) => r.data);
};

export const deleteFace = (userId: number) =>
  api.delete(`/faces/register/${userId}`);

export const identifyFace = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/faces/identify", form).then((r) => r.data);
};

// Attendance
export const getAttendance = (params?: Record<string, unknown>) =>
  api.get("/attendance/", { params }).then((r) => r.data);

export const getDailySummary = (date?: string) =>
  api.get("/attendance/summary/daily", { params: date ? { date } : {} }).then((r) => r.data);

export const createManualAttendance = (data: Record<string, unknown>) =>
  api.post("/attendance/manual", data).then((r) => r.data);

export const updateAttendance = (id: number, data: Record<string, unknown>) =>
  api.patch(`/attendance/${id}`, data).then((r) => r.data);

export const deleteAttendance = (id: number) =>
  api.delete(`/attendance/${id}`);

export const markFromPhoto = (file: File, cameraId?: number) => {
  const form = new FormData();
  form.append("file", file);
  if (cameraId) form.append("camera_id", String(cameraId));
  return api.post("/attendance/mark-photo", form).then((r) => r.data);
};

// Reports
export const getWeeklyReport = (params?: Record<string, unknown>) =>
  api.get("/reports/weekly", { params }).then((r) => r.data);

export const exportCSV = (params?: Record<string, unknown>) => {
  const url = new URL(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/reports/export/csv`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, String(v));
    });
  }
  const stored = localStorage.getItem("auth");
  const token = stored ? JSON.parse(stored).access_token : "";
  return fetch(url.toString(), { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => r.blob());
};

// Cameras
export const getCameras = () => api.get("/cameras/").then((r) => r.data);

export const createCamera = (data: Record<string, unknown>) =>
  api.post("/cameras/", data).then((r) => r.data);

export const updateCamera = (id: number, data: Record<string, unknown>) =>
  api.patch(`/cameras/${id}`, data).then((r) => r.data);

export const deleteCamera = (id: number) => api.delete(`/cameras/${id}`);
