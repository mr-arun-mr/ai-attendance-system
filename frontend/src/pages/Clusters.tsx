import { useEffect, useState } from "react";
import {
  getClusters, runClustering, getClusterSamples,
  linkCluster, rejectCluster, getUsers,
} from "../api";
import Modal from "../components/Modal";
import Badge from "../components/Badge";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

type ClusterStatus = "all" | "pending" | "linked" | "rejected";

interface Cluster {
  id: number;
  status: "pending" | "linked" | "rejected";
  sample_count: number;
  thumbnail_path: string | null;
  nearest_user_id: number | null;
  nearest_user_distance: number | null;
  linked_user_id: number | null;
  created_at: string | null;
}

interface User {
  id: number;
  full_name: string;
  employee_id: string;
}

interface Sample {
  id: number;
  thumbnail_path: string | null;
  captured_at: string | null;
}

const STATUS_TABS: { key: ClusterStatus; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pending", label: "Pending" },
  { key: "linked", label: "Linked" },
  { key: "rejected", label: "Rejected" },
];

const statusColor = (s: string) => {
  if (s === "linked") return "green";
  if (s === "rejected") return "red";
  return "yellow";
};

function thumbUrl(path: string | null): string | null {
  if (!path) return null;
  // thumbnail_path is stored as "/face_data/unknown_thumbs/filename.jpg"
  return `${API_BASE}${path}`;
}

export default function Clusters() {
  const [tab, setTab] = useState<ClusterStatus>("pending");
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

  // Detail modal state
  const [selected, setSelected] = useState<Cluster | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [linkUserId, setLinkUserId] = useState<string>("");
  const [actionLoading, setActionLoading] = useState(false);

  const load = (status: ClusterStatus) => {
    getClusters(status === "all" ? undefined : status)
      .then(setClusters)
      .catch(console.error);
  };

  useEffect(() => {
    load(tab);
    getUsers().then(setUsers).catch(console.error);
  }, []);

  const switchTab = (t: ClusterStatus) => {
    setTab(t);
    load(t);
  };

  const handleRunClustering = async () => {
    setRunning(true);
    setRunResult(null);
    try {
      const res = await runClustering();
      const { clustering, auto_link } = res;
      setRunResult(
        `Clustering: ${clustering.new_clusters} new clusters, ${clustering.noise_points} noise points. ` +
        `Auto-linked: ${auto_link.auto_linked}, hinted: ${auto_link.hinted}, unchanged: ${auto_link.unchanged}.`
      );
      load(tab);
    } catch (e: any) {
      setRunResult("Error: " + (e.response?.data?.detail ?? e.message));
    } finally {
      setRunning(false);
    }
  };

  const openDetail = async (cluster: Cluster) => {
    setSelected(cluster);
    setLinkUserId(cluster.nearest_user_id ? String(cluster.nearest_user_id) : "");
    setSamples([]);
    setLoadingSamples(true);
    try {
      const data = await getClusterSamples(cluster.id);
      setSamples(data);
    } catch {
      setSamples([]);
    } finally {
      setLoadingSamples(false);
    }
  };

  const handleLink = async () => {
    if (!selected || !linkUserId) return;
    setActionLoading(true);
    try {
      await linkCluster(selected.id, Number(linkUserId));
      setSelected(null);
      load(tab);
    } catch (e: any) {
      alert(e.response?.data?.detail ?? "Link failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (cluster: Cluster) => {
    if (!confirm(`Reject cluster #${cluster.id}? It will be excluded from future auto-link runs.`)) return;
    try {
      await rejectCluster(cluster.id);
      if (selected?.id === cluster.id) setSelected(null);
      load(tab);
    } catch (e: any) {
      alert(e.response?.data?.detail ?? "Reject failed");
    }
  };

  const userById = (id: number | null) => users.find((u) => u.id === id);

  const pendingCount = clusters.filter((c) => c.status === "pending").length;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Face Clusters</h1>
          <p className="text-sm text-gray-500 mt-1">
            Review unknown face groups detected by cameras and link them to registered users
          </p>
        </div>
        <div className="flex items-center gap-3">
          {runResult && (
            <p className="text-xs text-gray-600 max-w-xs text-right">{runResult}</p>
          )}
          <button
            onClick={handleRunClustering}
            disabled={running}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60 whitespace-nowrap"
          >
            {running ? "Running…" : "Run Clustering"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-xl p-1 w-fit">
        {STATUS_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => switchTab(key)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
            {key === "pending" && pendingCount > 0 && tab !== "pending" && (
              <span className="ml-1.5 bg-yellow-400 text-yellow-900 text-xs rounded-full px-1.5 py-0.5">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Cluster grid */}
      {clusters.length === 0 ? (
        <div className="text-center py-16 text-gray-400 text-sm">
          No clusters found. Run clustering to process buffered unknown faces.
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {clusters.map((c) => {
            const hint = userById(c.nearest_user_id);
            const linked = userById(c.linked_user_id);
            const thumb = thumbUrl(c.thumbnail_path);
            return (
              <div
                key={c.id}
                className="bg-white rounded-2xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow cursor-pointer group"
                onClick={() => openDetail(c)}
              >
                {/* Thumbnail */}
                <div className="aspect-square bg-gray-100 relative overflow-hidden">
                  {thumb ? (
                    <img
                      src={thumb}
                      alt={`Cluster #${c.id}`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-300 text-4xl">
                      ?
                    </div>
                  )}
                  <div className="absolute top-2 right-2">
                    <Badge
                      label={c.status}
                      color={statusColor(c.status) as any}
                    />
                  </div>
                </div>

                {/* Info */}
                <div className="p-3">
                  <p className="text-xs font-semibold text-gray-700">Cluster #{c.id}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {c.sample_count} sample{c.sample_count !== 1 ? "s" : ""}
                  </p>
                  {linked ? (
                    <p className="text-xs text-green-700 mt-1 truncate">
                      Linked: {linked.full_name}
                    </p>
                  ) : hint ? (
                    <p className="text-xs text-yellow-700 mt-1 truncate">
                      Hint: {hint.full_name} ({c.nearest_user_distance?.toFixed(2)})
                    </p>
                  ) : (
                    <p className="text-xs text-gray-400 mt-1">No match hint</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail modal */}
      {selected && (
        <Modal
          title={`Cluster #${selected.id} — ${selected.sample_count} samples`}
          onClose={() => setSelected(null)}
          wide
        >
          <div className="space-y-4">
            {/* Status row */}
            <div className="flex items-center gap-2">
              <Badge label={selected.status} color={statusColor(selected.status) as any} />
              {selected.nearest_user_distance != null && (
                <span className="text-xs text-gray-500">
                  Nearest distance: {selected.nearest_user_distance.toFixed(4)}
                </span>
              )}
              {selected.created_at && (
                <span className="text-xs text-gray-400 ml-auto">
                  {new Date(selected.created_at).toLocaleDateString()}
                </span>
              )}
            </div>

            {/* Sample face grid */}
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">
                Face Samples
              </p>
              {loadingSamples ? (
                <p className="text-sm text-gray-400 py-4 text-center">Loading samples…</p>
              ) : samples.length === 0 ? (
                <p className="text-sm text-gray-400 py-4 text-center">No samples available.</p>
              ) : (
                <div className="grid grid-cols-6 gap-2 max-h-56 overflow-y-auto">
                  {samples.map((s) => {
                    const url = thumbUrl(s.thumbnail_path);
                    return url ? (
                      <img
                        key={s.id}
                        src={url}
                        alt="face sample"
                        className="aspect-square object-cover rounded-lg"
                        title={s.captured_at ? new Date(s.captured_at).toLocaleString() : ""}
                      />
                    ) : (
                      <div
                        key={s.id}
                        className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center text-gray-300 text-xs"
                      >
                        ?
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Link to user section */}
            {selected.status !== "rejected" && (
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">
                  Link to User
                </p>
                <div className="flex gap-2">
                  <select
                    value={linkUserId}
                    onChange={(e) => setLinkUserId(e.target.value)}
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="">Select a person…</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.employee_id})
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleLink}
                    disabled={actionLoading || !linkUserId || selected.status === "linked"}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                  >
                    {actionLoading ? "Linking…" : selected.status === "linked" ? "Already linked" : "Link"}
                  </button>
                </div>
                {selected.nearest_user_id && (
                  <p className="text-xs text-yellow-700 mt-1.5">
                    Suggested: {userById(selected.nearest_user_id)?.full_name ?? `User #${selected.nearest_user_id}`}
                    {" "}(distance {selected.nearest_user_distance?.toFixed(4)})
                  </p>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-1">
              {selected.status === "pending" && (
                <button
                  onClick={() => handleReject(selected)}
                  className="px-4 py-2 rounded-lg text-sm border border-red-300 text-red-600 hover:bg-red-50"
                >
                  Reject cluster
                </button>
              )}
              <button
                onClick={() => setSelected(null)}
                className="ml-auto px-4 py-2 rounded-lg text-sm border border-gray-300 text-gray-600 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
