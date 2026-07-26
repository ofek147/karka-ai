interface Props {
  size?: "sm" | "md" | "lg";
  dark?: boolean; // true = white text (for dark bg), false = dark text
}

export default function KarkaLogo({ size = "md", dark = true }: Props) {
  const textSize = size === "sm" ? "text-lg" : size === "lg" ? "text-4xl" : "text-2xl";
  const base = dark ? "text-white" : "text-[#0d1829]";

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
