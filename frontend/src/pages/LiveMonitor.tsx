import { useEffect, useRef, useState } from "react";
import { getCameras, identifyFace, markFromPhoto } from "../api";
import Badge from "../components/Badge";

interface Camera {
  id: number;
  name: string;
  location: string | null;
  stream_url: string;
  is_active: boolean;
}

interface Detection {
  user_id: number;
  name: string;
  confidence: number;
  marked: boolean;
}

interface VideoResult {
  frameIndex: number;
  timestamp: string;
  user_id?: number;
  full_name?: string;
  employee_id?: string;
  confidence?: number;
  marked?: boolean;
  reason?: string;
}

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000").replace(/\/$/, "");

type Tab = "live" | "test";

export default function LiveMonitor() {
  const [tab, setTab] = useState<Tab>("live");

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Live Monitor</h1>
        <p className="text-sm text-gray-500 mt-1">
          Real-time face recognition and offline testing
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit mb-6">
        <button
          onClick={() => setTab("live")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "live" ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Live Camera
        </button>
        <button
          onClick={() => setTab("test")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "test" ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Test Mode
        </button>
      </div>

      {tab === "live" ? <LiveTab /> : <TestTab />}
    </div>
  );
}

/* ─── Live Camera Tab ─────────────────────────────────────────── */

function LiveTab() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCam, setSelectedCam] = useState<Camera | null>(null);
  const [frame, setFrame] = useState<string | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [connected, setConnected] = useState(false);
  const [useWebcam, setUseWebcam] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getCameras().then(setCameras).catch(console.error);
  }, []);

  const connectWs = (cam: Camera) => {
    if (wsRef.current) wsRef.current.close();
    const auth = localStorage.getItem("auth");
    const token = auth ? JSON.parse(auth).access_token : "";
    const ws = new WebSocket(`${WS_BASE}/ws/camera/${cam.id}?token=${token}`);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "frame") {
        setFrame(`data:image/jpeg;base64,${msg.jpeg}`);
        setDetections(msg.detections || []);
      }
    };
    wsRef.current = ws;
  };

  const startWebcam = async (cam: Camera) => {
    if (!navigator.mediaDevices) return;
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    }
    connectWs(cam);
    intervalRef.current = setInterval(() => {
      if (!canvasRef.current || !videoRef.current || !wsRef.current) return;
      const ctx = canvasRef.current.getContext("2d");
      if (!ctx) return;
      canvasRef.current.width = videoRef.current.videoWidth;
      canvasRef.current.height = videoRef.current.videoHeight;
      ctx.drawImage(videoRef.current, 0, 0);
      canvasRef.current.toBlob(
        (blob) => {
          if (blob && wsRef.current?.readyState === WebSocket.OPEN) {
            blob.arrayBuffer().then((buf) => wsRef.current?.send(buf));
          }
        },
        "image/jpeg",
        0.7
      );
    }, 500);
  };

  const stop = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (wsRef.current) wsRef.current.close();
    if (videoRef.current?.srcObject) {
      (videoRef.current.srcObject as MediaStream).getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setConnected(false);
    setFrame(null);
    setDetections([]);
  };

  const handleStart = () => {
    if (!selectedCam) return;
    if (useWebcam) startWebcam(selectedCam);
    else connectWs(selectedCam);
  };

  useEffect(() => stop, []);

  return (
    <>
      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-2xl p-5 mb-6 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Camera</label>
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={selectedCam?.id ?? ""}
            onChange={(e) => {
              const cam = cameras.find((c) => c.id === Number(e.target.value));
              setSelectedCam(cam ?? null);
            }}
          >
            <option value="">Select a camera…</option>
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}{c.location ? ` (${c.location})` : ""}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={useWebcam}
            onChange={(e) => setUseWebcam(e.target.checked)}
            className="rounded"
          />
          Use browser webcam
        </label>
        <button
          disabled={!selectedCam}
          onClick={connected ? stop : handleStart}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            connected
              ? "bg-red-500 text-white hover:bg-red-600"
              : "bg-blue-600 text-white hover:bg-blue-700"
          } disabled:opacity-40`}
        >
          {connected ? "Stop" : "Start"}
        </button>
        <Badge label={connected ? "Live" : "Offline"} color={connected ? "green" : "gray"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-black rounded-2xl overflow-hidden aspect-video flex items-center justify-center">
          <video ref={videoRef} className="hidden" />
          <canvas ref={canvasRef} className="hidden" />
          {frame ? (
            <img src={frame} alt="Live feed" className="w-full h-full object-contain" />
          ) : (
            <p className="text-gray-500 text-sm">
              {connected ? "Waiting for frames…" : "Camera not started"}
            </p>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold mb-3">Detections</h2>
          {detections.length === 0 ? (
            <p className="text-xs text-gray-400">No faces detected</p>
          ) : (
            <div className="space-y-3">
              {detections.map((d, i) => (
                <div key={i} className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                  <p className="text-sm font-medium">{d.name}</p>
                  <p className="text-xs text-gray-500">
                    Confidence: {(d.confidence * 100).toFixed(1)}%
                  </p>
                  {d.marked && <span className="text-xs text-green-600 font-medium">✓ Marked</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ─── Test Mode Tab ───────────────────────────────────────────── */

function TestTab() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <PhotoTest />
      <VideoTest />
    </div>
  );
}

/* Photo test */
function PhotoTest() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleIdentify = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const data = await identifyFace(file);
      setResult(data);
    } catch (e: any) {
      setResult({ error: e.response?.data?.detail ?? "Error" });
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAttendance = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const data = await markFromPhoto(file);
      setResult(data);
    } catch (e: any) {
      setResult({ error: e.response?.data?.detail ?? "Error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold mb-1">Photo Test</h2>
      <p className="text-xs text-gray-500 mb-4">
        Upload a photo to identify the person or mark attendance.
      </p>

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />

      {/* Drop zone */}
      <div
        onClick={() => fileRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors mb-4"
      >
        {preview ? (
          <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-lg object-contain" />
        ) : (
          <div>
            <p className="text-3xl mb-2">📷</p>
            <p className="text-sm text-gray-500">Click or drag a photo here</p>
          </div>
        )}
      </div>

      {file && (
        <div className="flex gap-3 mb-4">
          <button
            onClick={handleIdentify}
            disabled={loading}
            className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Identifying…" : "Identify"}
          </button>
          <button
            onClick={handleMarkAttendance}
            disabled={loading}
            className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60"
          >
            {loading ? "Marking…" : "Mark Attendance"}
          </button>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="rounded-xl bg-gray-50 border border-gray-200 p-4 text-sm">
          {result.error ? (
            <p className="text-red-600">{result.error}</p>
          ) : result.match ? (
            <div className="space-y-1">
              <p className="font-semibold text-green-700">Match found</p>
              <p><span className="text-gray-500">Name:</span> {result.match.full_name}</p>
              <p><span className="text-gray-500">ID:</span> {result.match.employee_id}</p>
              <p>
                <span className="text-gray-500">Confidence:</span>{" "}
                {(result.match.confidence * 100).toFixed(1)}%
              </p>
            </div>
          ) : result.marked === true ? (
            <div className="space-y-1">
              <p className="font-semibold text-green-700">Attendance marked</p>
              <p><span className="text-gray-500">User ID:</span> {result.user_id}</p>
              <p><span className="text-gray-500">Confidence:</span> {(result.confidence * 100).toFixed(1)}%</p>
            </div>
          ) : result.marked === false ? (
            <p className="text-yellow-700">{result.reason}</p>
          ) : (
            <p className="text-gray-500">No matching face found</p>
          )}
        </div>
      )}
    </div>
  );
}

/* Video test */
function VideoTest() {
  const [file, setFile] = useState<File | null>(null);
  const [fps, setFps] = useState(1);
  const [results, setResults] = useState<VideoResult[]>([]);
  const [progress, setProgress] = useState(0); // 0–100
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const stopRef = useRef(false);

  const handleFile = (f: File) => {
    setFile(f);
    setResults([]);
    setProgress(0);
    setDone(false);
  };

  const extractFrameBlob = (video: HTMLVideoElement, canvas: HTMLCanvasElement): Promise<Blob> =>
    new Promise((resolve, reject) => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return reject("No canvas context");
      ctx.drawImage(video, 0, 0);
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject("Blob null")),
        "image/jpeg",
        0.75
      );
    });

  const seekTo = (video: HTMLVideoElement, time: number): Promise<void> =>
    new Promise((resolve) => {
      video.currentTime = time;
      video.onseeked = () => resolve();
    });

  const runTest = async () => {
    if (!file || !videoRef.current || !canvasRef.current) return;
    stopRef.current = false;
    setRunning(true);
    setResults([]);
    setDone(false);
    setProgress(0);

    const video = videoRef.current;
    const canvas = canvasRef.current;

    video.src = URL.createObjectURL(file);
    await new Promise<void>((resolve) => {
      video.onloadedmetadata = () => resolve();
    });

    const duration = video.duration;
    const step = 1 / fps;
    const times: number[] = [];
    for (let t = 0; t < duration; t += step) times.push(t);

    for (let i = 0; i < times.length; i++) {
      if (stopRef.current) break;
      await seekTo(video, times[i]);
      try {
        const blob = await extractFrameBlob(video, canvas);
        const f = new File([blob], "frame.jpg", { type: "image/jpeg" });
        const data = await markFromPhoto(f);
        const ts = new Date(times[i] * 1000).toISOString().substr(11, 8);
        setResults((prev) => [
          ...prev,
          {
            frameIndex: i + 1,
            timestamp: ts,
            ...data,
          },
        ]);
      } catch {
        // skip unreadable frame
      }
      setProgress(Math.round(((i + 1) / times.length) * 100));
    }

    setRunning(false);
    setDone(true);
    URL.revokeObjectURL(video.src);
  };

  const stopTest = () => {
    stopRef.current = true;
  };

  const marked = results.filter((r) => r.marked);
  const uniqueIds = [...new Set(marked.map((r) => r.user_id))];

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 flex flex-col">
      <h2 className="text-base font-semibold mb-1">Video File Test</h2>
      <p className="text-xs text-gray-500 mb-4">
        Upload an MP4 / MOV / AVI. Frames are extracted in-browser and sent to the recognition
        pipeline to simulate a live camera feed.
      </p>

      <video ref={videoRef} className="hidden" />
      <canvas ref={canvasRef} className="hidden" />
      <input
        ref={fileRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />

      {/* Drop zone */}
      <div
        onClick={() => !running && fileRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors mb-4 ${
          running
            ? "border-gray-200 bg-gray-50 cursor-default"
            : "border-gray-300 cursor-pointer hover:border-blue-400 hover:bg-blue-50"
        }`}
      >
        {file ? (
          <div>
            <p className="text-2xl mb-1">🎬</p>
            <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
            <p className="text-xs text-gray-400">{(file.size / 1e6).toFixed(1)} MB</p>
          </div>
        ) : (
          <div>
            <p className="text-3xl mb-2">🎬</p>
            <p className="text-sm text-gray-500">Click or drag a video file here</p>
            <p className="text-xs text-gray-400 mt-1">MP4, MOV, AVI, WebM</p>
          </div>
        )}
      </div>

      {/* FPS selector */}
      <div className="flex items-center gap-3 mb-4">
        <label className="text-xs font-medium text-gray-600 whitespace-nowrap">
          Frames per second:
        </label>
        <select
          value={fps}
          onChange={(e) => setFps(Number(e.target.value))}
          disabled={running}
          className="border border-gray-300 rounded-lg px-2 py-1 text-sm"
        >
          <option value={0.5}>0.5 fps (1 frame / 2 s)</option>
          <option value={1}>1 fps</option>
          <option value={2}>2 fps</option>
          <option value={5}>5 fps</option>
        </select>
      </div>

      {/* Run/Stop button */}
      <div className="flex gap-3 mb-4">
        <button
          onClick={running ? stopTest : runTest}
          disabled={!file}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 ${
            running
              ? "bg-red-500 text-white hover:bg-red-600"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {running ? "Stop" : "Run Test"}
        </button>
        {(results.length > 0 || done) && !running && (
          <button
            onClick={() => { setResults([]); setProgress(0); setDone(false); }}
            className="px-4 py-2 rounded-lg text-sm border border-gray-300 hover:bg-gray-50"
          >
            Clear
          </button>
        )}
      </div>

      {/* Progress bar */}
      {(running || done) && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{running ? "Processing…" : "Done"}</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${done ? "bg-green-500" : "bg-blue-500"}`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Summary */}
      {results.length > 0 && (
        <div className="mb-3 p-3 rounded-xl bg-blue-50 border border-blue-100 text-sm">
          <p className="font-semibold text-blue-800">
            {marked.length} attendance mark{marked.length !== 1 ? "s" : ""} across{" "}
            {uniqueIds.length} person{uniqueIds.length !== 1 ? "s" : ""}
          </p>
        </div>
      )}

      {/* Per-frame results */}
      {results.length > 0 && (
        <div className="flex-1 overflow-y-auto max-h-64 space-y-2 pr-1">
          {results.map((r, i) => (
            <div
              key={i}
              className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs border ${
                r.marked
                  ? "bg-green-50 border-green-200"
                  : r.marked === false
                  ? "bg-yellow-50 border-yellow-200"
                  : "bg-gray-50 border-gray-200"
              }`}
            >
              <span className="text-gray-400 font-mono w-14 shrink-0">
                {r.timestamp}
              </span>
              <span className="flex-1 font-medium px-2 truncate">
                {r.full_name ?? (r.reason ?? "No face")}
              </span>
              {r.confidence != null && (
                <span className="text-gray-500 shrink-0">
                  {(r.confidence * 100).toFixed(0)}%
                </span>
              )}
              {r.marked && (
                <span className="ml-2 text-green-600 font-semibold shrink-0">✓</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
