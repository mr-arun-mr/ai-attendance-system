# AI Attendance System

A full-stack, AI-powered attendance system that uses face recognition to automatically mark attendance from live camera feeds or uploaded photos and videos — no manual check-ins required.

---

## Features

- **Automatic attendance** — cameras stream frames to the backend; recognized faces are checked in instantly
- **Face registration wizard** — upload 3–10 photos per person; embeddings are averaged for accuracy
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
| AI / CV | Python, OpenCV, face_recognition (dlib) |
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
│   ├── Dockerfile.dev
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios client + all API calls
│   │   ├── components/     # Layout, Modal, StatCard, Badge
│   │   ├── context/        # AuthContext (JWT storage)
│   │   └── pages/          # Dashboard, LiveMonitor, People, AttendanceLogs, Reports, Settings
│   ├── nginx.conf
│   ├── Dockerfile
│   └── Dockerfile.dev
├── docker-compose.yml       # Production
├── docker-compose.dev.yml   # Development (hot reload)
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

### 3. Default login

```
Email:    admin@attendance.local
Password: admin123
```

> Change the admin password after first login via the People page.

---

## Development Setup (Hot Reload)

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- Backend reloads on file save (Uvicorn `--reload`)
- Frontend hot-reloads via Vite dev server on port `3000`

---

## How to Use

### Step 1 — Add departments (optional)
Go to **Settings → Departments** and add your departments (e.g. Engineering, HR).

### Step 2 — Add people
Go to **People → Add Person**, fill in the form, then click **Face** to open the face registration wizard. Upload 3–10 clear face photos. The system averages the embeddings for better recognition accuracy.

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
| POST | `/faces/identify` | Identify a face from a photo |
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
  → Cosine similarity vs. stored embeddings
  → If match AND not already marked today → INSERT attendance_log
  → Annotated JPEG + detection JSON → frontend
```

### Face registration
```
Admin uploads N photos
  → POST /faces/register/{user_id}
  → Extract embedding from each photo
  → Average all embeddings into one vector
  → Store in face_embeddings table
```

---

## Database Schema

Five tables are created automatically on first startup via SQLAlchemy `create_all`.

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
| `embedding` | text | NOT NULL — JSON array of 128 floats (averaged across registration photos) |
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

---

## Production Notes

- Replace `SECRET_KEY` in `.env` with a long random string before deploying
- Mount `/app/face_data` as a persistent volume (already configured in `docker-compose.yml`)
- The `face_recognition` library requires `cmake` and `dlib` — the Dockerfile handles this with a multi-stage build
- For high-resolution cameras or multiple simultaneous feeds, consider running the backend with multiple Uvicorn workers
