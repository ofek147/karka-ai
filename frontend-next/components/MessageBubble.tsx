import { Message } from "@/lib/types";

interface Props {
  message: Message;
}

function formatContent(text: string) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    const boldified = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    const withH = boldified.replace(/^#+\s+(.*)/, "<strong>$1</strong>");
    return <p key={i} dangerouslySetInnerHTML={{ __html: withH || "&nbsp;" }} />;
  });
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[78%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm leading-relaxed bg-[#1e293b] text-slate-100 shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-end mb-4 gap-2.5">
      <div className="max-w-[80%] flex flex-col gap-1">
        <div className="px-4 py-3 rounded-2xl rounded-tl-sm text-sm leading-relaxed bg-white border border-[#c4a044]/20 text-[#0f172a] shadow-sm ai-message">
          {formatContent(message.content)}
        </div>
      </div>
      {/* AI avatar */}
      <div className="shrink-0 w-7 h-7 rounded-full bg-[#c4a044]/15 border border-[#c4a044]/30 flex items-center justify-center text-[#c4a044] text-xs font-bold mt-0.5">
        ◈
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-end mb-4 gap-2.5">
      <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white border border-[#c4a044]/20 shadow-sm">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 bg-[#c4a044] rounded-full"
              style={{
                animation: "pulse-dot 1.2s ease-in-out infinite",
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      </div>
      <div className="shrink-0 w-7 h-7 rounded-full bg-[#c4a044]/15 border border-[#c4a044]/30 flex items-center justify-center text-[#c4a044] text-xs font-bold mt-0.5">
        ◈
      </div>
    </div>
  );
}
