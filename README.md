# AI Attendance System

A full-stack, AI-powered attendance system that uses face recognition to automatically mark attendance from live camera feeds or uploaded photos and videos — no manual check-ins required.

---

## Features

- **Automatic attendance** — cameras stream frames to the backend; recognized faces are checked in instantly
- **Face registration wizard** — upload 1–10 photos per person; each photo's embedding is stored separately so every angle is available for matching
- **CCTV-domain enrollment** — append a live-camera frame directly to a user's embeddings to close the HD-photo vs. CCTV resolution gap
- **Unknown face clustering** — unrecognised faces are buffered and grouped by identity using DBSCAN; confident matches are auto-linked to registered users; borderline matches surface in an admin review queue
- **Live monitor** — real-time annotated video feed with bounding boxes and name labels
- **Test Mode** — test without a camera by uploading a photo or video file
- **Attendance logs** — filterable table with manual entry, checkout, and delete
- **Reports** — 7-day bar chart, daily summary stats, CSV export with date/department filters
- **Department & camera management** — all configuration done through the UI
- **JWT authentication** — role-based access (admin vs. viewer)

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI / CV | Python, OpenCV, face_recognition (dlib), scikit-learn (DBSCAN clustering) |
| Backend | FastAPI, SQLAlchemy (async), PostgreSQL, WebSockets |
| Frontend | React 18, Vite, TailwindCSS, Recharts |
| Infrastructure | Docker, Docker Compose, Nginx |
| Auth | JWT (python-jose + passlib/bcrypt) |

---

## Project Structure

```
ai-attendance-system/
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers (auth, users, faces, attendance, reports, cameras, WebSocket)
│   │   ├── core/           # Config, database session, JWT security
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   └── services/       # Face recognition logic, attendance service
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios client + all API calls
│   │   ├── components/     # Layout, Modal, StatCard, Badge
│   │   ├── context/        # AuthContext (JWT storage)
│   │   └── pages/          # Dashboard, LiveMonitor, People, AttendanceLogs, Reports, Settings
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── .env.example
```

---

## Quick Start (Docker)

### 1. Clone and configure

```bash
git clone <repo-url>
cd ai-attendance-system
cp .env.example .env
```

Edit `.env` if you want to change passwords or the admin credentials. Defaults work out of the box.

### 2. Build and run

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

Backend reloads on file save (Uvicorn `--reload`), frontend hot-reloads via Vite dev server.

### 3. Default login

```
Email:    admin@attendance.local
Password: admin123
```

> Change the admin password after first login via the People page.

---

## How to Use

### Step 1 — Add departments (optional)
Go to **Settings → Departments** and add your departments (e.g. Engineering, HR).

### Step 2 — Add people
Go to **People → Add Person**, fill in the form, then click **Face** to open the face registration wizard. Upload 1–10 clear face photos from different angles. Each photo is stored as a separate embedding so the system can match the person even when the camera angle varies.

**Optional — CCTV-domain enrollment:** after starting the live monitor, you can capture a frame of the person and register it directly via `POST /faces/register-from-frame/{id}`. This adds a low-resolution, real-lighting reference that reduces false negatives from the HD-vs-CCTV domain gap.

### Step 3 — Add cameras (for live feed)
Go to **Settings → Cameras** and add your camera with its RTSP or HTTP stream URL.

### Step 4 — Start the live monitor
Go to **Live Monitor → Live Camera**, select a camera, optionally tick "Use browser webcam", and click **Start**. Recognized faces are checked in automatically and the annotated feed is shown in real time.

### Step 5 — View results
- **Dashboard** — today's present / absent / late counts and recent check-ins
- **Attendance Logs** — filter by date and department, manually add or edit records, mark checkouts
- **Reports** — 7-day trend chart, export CSV for any date range

---

## Testing Without a Camera

Go to **Live Monitor → Test Mode**:

### Photo Test
Upload a single JPEG or PNG image and choose:
- **Identify** — returns the matched person's name, employee ID, and confidence score
- **Mark Attendance** — runs the full check-in pipeline and reports the outcome

### Video File Test
Upload any MP4, MOV, AVI, or WebM file:
1. Choose an extraction rate (0.5 – 5 fps)
2. Click **Run Test**
3. Frames are extracted in-browser using HTML5 Canvas and sent to the recognition pipeline one by one
4. A timestamped per-frame log shows who was detected, confidence %, and whether attendance was marked
5. A summary shows total marks and unique people identified

---

## API Reference

Interactive documentation is available at **http://localhost:8000/docs** when the backend is running.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Get JWT token |
| GET | `/users/` | List all users |
| POST | `/users/` | Create user (admin) |
| POST | `/users/{id}/photo` | Upload profile photo |
| POST | `/faces/register/{id}` | Register face from photos |
| DELETE | `/faces/register/{id}` | Remove face data |
| POST | `/faces/register-from-frame/{id}` | Append a CCTV-domain frame embedding to a user |
| POST | `/faces/identify` | Identify a face from a photo |
| GET | `/clusters/` | List unknown-face clusters (admin) |
| POST | `/clusters/run` | Run DBSCAN clustering + auto-link (admin) |
| POST | `/clusters/{id}/link` | Manually assign a cluster to a user (admin) |
| POST | `/clusters/{id}/reject` | Reject a cluster (admin) |
| GET | `/attendance/` | List attendance logs |
| POST | `/attendance/mark-photo` | Mark attendance from a photo |
| POST | `/attendance/manual` | Manual attendance entry (admin) |
| PATCH | `/attendance/{id}` | Update a log (admin) |
| GET | `/attendance/summary/daily` | Today's summary stats |
| GET | `/reports/weekly` | 7-day attendance data |
| GET | `/reports/export/csv` | Download CSV report |
| GET | `/cameras/` | List cameras |
| POST | `/cameras/` | Add a camera (admin) |
| WS | `/ws/camera/{id}` | WebSocket live feed — send JPEG bytes, receive annotated frames |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `SECRET_KEY` | `change-me-...` | JWT signing key — **change in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token lifetime (8 hours) |
| `RECOGNITION_THRESHOLD` | `0.55` | Face match threshold (lower = stricter) |
| `ADMIN_EMAIL` | `admin@attendance.local` | Seed admin email |
| `ADMIN_PASSWORD` | `admin123` | Seed admin password |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL used by the frontend |
| `VITE_WS_URL` | `ws://localhost:8000` | WebSocket URL used by the frontend |

---

## Data Flow

### Attendance marking (live camera)
```
Camera frame (JPEG bytes)
  → WebSocket /ws/camera/{id}
  → Face detection (OpenCV)
  → Embedding extraction (face_recognition / dlib)
  → L2 distance vs. all stored embeddings (best match wins)
  → If match AND not already marked today → INSERT attendance_log
  → Unmatched faces → buffered as UnknownFaceCapture (with dedup)
  → Annotated JPEG + detection JSON → frontend
```

### Face registration
```
Admin uploads N photos
  → POST /faces/register/{user_id}
  → Extract embedding from each photo independently
  → Store one face_embeddings row per photo (angle preserved)
```

### Unknown face clustering (admin-triggered)
```
POST /clusters/run
  → Load all un-clustered UnknownFaceCapture rows
  → DBSCAN (eps=0.50, min_samples=3) groups them by identity
  → For each cluster: compute centroid embedding
  → Compare centroid vs. all registered FaceEmbeddings
      L2 < 0.45  → auto-link: append centroid as new FaceEmbedding
      0.45–0.60  → pending with nearest-user hint for admin review
      ≥ 0.60     → pending, no hint (genuinely unknown person)
```

---

## Database Schema

Seven tables are created automatically on first startup via SQLAlchemy `create_all`.

### `departments`

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, auto-increment |
| `name` | varchar(100) | NOT NULL, UNIQUE |
| `created_at` | timestamptz | server default `now()` |

### `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, auto-increment |
| `email` | varchar(255) | NOT NULL, UNIQUE |
| `full_name` | varchar(200) | NOT NULL |
| `employee_id` | varchar(50) | NOT NULL, UNIQUE |
| `hashed_password` | varchar(255) | NOT NULL |
| `is_active` | boolean | default `true` |
| `is_admin` | boolean | default `false` |
| `department_id` | integer | FK → `departments.id`, nullable |
| `photo_path` | varchar(500) | nullable |
| `created_at` | timestamptz | server default `now()` |

### `face_embeddings`

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, auto-increment |
| `user_id` | integer | FK → `users.id` ON DELETE CASCADE, NOT NULL |
| `embedding` | text | NOT NULL — JSON array of 128 floats; one row per registered photo or auto-linked cluster centroid |
| `created_at` | timestamptz | server default `now()` |

### `cameras`

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, auto-increment |
| `name` | varchar(100) | NOT NULL |
| `location` | varchar(200) | nullable |
| `stream_url` | varchar(500) | NOT NULL |
| `is_active` | boolean | default `true` |
| `created_at` | timestamptz | server default `now()` |

### `attendance_logs`

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, auto-increment |
| `user_id` | integer | FK → `users.id`, NOT NULL |
| `check_in` | timestamptz | NOT NULL |
| `check_out` | timestamptz | nullable |
| `date` | date | NOT NULL |
| `confidence` | float | nullable — face-match score from recognition engine |
| `source` | varchar(50) | default `'camera'` — `camera` or `manual` |
| `camera_id` | integer | FK → `cameras.id`, nullable |
| `is_late` | boolean | default `false` — true when check-in is after work start time |
| `created_at` | timestamptz | server default `now()` |

### `unknown_face_captures`

Temporary buffer of unrecognised faces seen by cameras. Rows are grouped into clusters by `POST /clusters/run` and can be pruned once clustered.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, auto-increment |
| `embedding` | varchar(8192) | NOT NULL — JSON array of 128 floats |
| `thumbnail_path` | varchar(500) | nullable — relative path under `/face_data/unknown_thumbs/` |
| `camera_id` | integer | FK → `cameras.id` ON DELETE SET NULL, nullable |
| `captured_at` | timestamptz | server default `now()` |
| `cluster_id` | integer | FK → `face_clusters.id` ON DELETE SET NULL, nullable — set after clustering |

### `face_clusters`

One row per inferred identity discovered by DBSCAN clustering of unknown captures.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, auto-increment |
| `centroid` | varchar(8192) | NOT NULL — mean embedding of all member captures |
| `sample_count` | integer | number of captures in the cluster |
| `thumbnail_path` | varchar(500) | nullable — thumbnail of the capture closest to the centroid |
| `nearest_user_id` | integer | FK → `users.id` ON DELETE SET NULL, nullable — closest registered user (hint) |
| `nearest_user_distance` | float | nullable — L2 distance to `nearest_user_id` |
| `linked_user_id` | integer | FK → `users.id` ON DELETE SET NULL, nullable — set when linked |
| `status` | varchar(20) | `pending` / `linked` / `rejected` |
| `created_at` | timestamptz | server default `now()` |
| `updated_at` | timestamptz | server default `now()`, updated on change |

---

## Production Notes

- Replace `SECRET_KEY` in `.env` with a long random string before deploying
- Mount `/app/face_data` as a persistent volume (already configured in `docker-compose.yml`)
- The `face_recognition` library requires `cmake` and `dlib` — the backend Dockerfile installs these at build time
- For high-resolution cameras or multiple simultaneous feeds, consider running the backend with multiple Uvicorn workers
