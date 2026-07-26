interface Props {
  size?: "sm" | "md" | "lg";
}

export default function KarkaLogo({ size = "md" }: Props) {
  const textSize = size === "sm" ? "text-lg" : size === "lg" ? "text-4xl" : "text-2xl";
  const base = "text-white";

  return (
    <span className={`font-bold tracking-tight ${textSize} ${base} select-none`}>
      kark
      <span
        style={{
          color: "#c4a044",
          fontStyle: "italic",
          fontSize: "1.15em",
          lineHeight: 1,
          letterSpacing: "-0.02em",
        }}
      >
        A
      </span>
      <span>i</span>
    </span>
  );
}
