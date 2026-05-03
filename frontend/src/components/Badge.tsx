interface Props {
  label: string;
  color?: "green" | "red" | "yellow" | "blue" | "gray";
}

const palette = {
  green: "bg-green-100 text-green-800",
  red: "bg-red-100 text-red-800",
  yellow: "bg-yellow-100 text-yellow-800",
  blue: "bg-blue-100 text-blue-800",
  gray: "bg-gray-100 text-gray-700",
};

export default function Badge({ label, color = "gray" }: Props) {
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${palette[color]}`}>
      {label}
    </span>
  );
}
