interface Props {
  label: string;
  value: number | string;
  sub?: string;
  color?: string;
}

export default function StatCard({ label, value, sub, color = "blue" }: Props) {
  const colors: Record<string, string> = {
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    green: "bg-green-50 border-green-200 text-green-700",
    red: "bg-red-50 border-red-200 text-red-700",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
  };
  return (
    <div className={`rounded-xl border p-5 ${colors[color] ?? colors.blue}`}>
      <p className="text-sm font-medium opacity-70">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-60">{sub}</p>}
    </div>
  );
}
