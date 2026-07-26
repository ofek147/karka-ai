interface Props {
  size?: number;
  bgOpacity?: number; // 0 = transparent bg, 1 = full navy bg
}

export default function KarkaIcon({ size = 28, bgOpacity = 1 }: Props) {
  return (
    <svg width={size} height={size} viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="80" height="80" rx="18" fill="#0d1829" fillOpacity={bgOpacity}/>
      <path d="M40 8 L72 40 L40 72 L8 40 Z" fill="none" stroke="#c4a044" strokeWidth="3"/>
      <line x1="40" y1="8" x2="40" y2="72" stroke="#c4a044" strokeWidth="1" strokeOpacity="0.3"/>
      <line x1="8" y1="40" x2="72" y2="40" stroke="#c4a044" strokeWidth="1" strokeOpacity="0.3"/>
      <circle cx="40" cy="40" r="10" fill="none" stroke="#c4a044" strokeWidth="1.2" strokeOpacity="0.35"/>
      <circle cx="40" cy="40" r="5" fill="#c4a044"/>
    </svg>
  );
}
