import { useEffect, useRef, useState } from "react";
import { getCameras } from "../api";
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

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000").replace(/\/$/, "");

export default function LiveMonitor() {
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
    if (wsRef.current) {
      wsRef.current.close();
    }
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
    // Send frames at 2 fps
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
      (videoRef.current.srcObject as MediaStream)
        .getTracks()
        .forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setConnected(false);
    setFrame(null);
    setDetections([]);
  };

  const handleStart = () => {
    if (!selectedCam) return;
    if (useWebcam) {
      setUseWebcam(true);
      startWebcam(selectedCam);
    } else {
      connectWs(selectedCam);
    }
  };

  useEffect(() => stop, []); // cleanup on unmount

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Live Monitor</h1>
        <p className="text-sm text-gray-500 mt-1">
          Real-time face recognition from camera feeds
        </p>
      </div>

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
        {/* Video/frame */}
        <div className="lg:col-span-2 bg-black rounded-2xl overflow-hidden aspect-video flex items-center justify-center relative">
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

        {/* Detections */}
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
                  {d.marked && (
                    <span className="text-xs text-green-600 font-medium">✓ Marked</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
