import { Message } from "@/lib/types";

interface Props {
  message: Message;
}

function formatContent(text: string) {
  // Simple markdown: **bold**, bullet lists
  const lines = text.split("\n");
  return lines.map((line, i) => {
    const boldified = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    return <p key={i} dangerouslySetInnerHTML={{ __html: boldified || "&nbsp;" }} />;
  });
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-start" : "justify-end"} mb-3`}>
      <div
        className={`
          max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? "bg-blue-600 text-white rounded-tr-sm"
            : "bg-gray-100 text-gray-800 rounded-tl-sm ai-message"}
        `}
      >
        {formatContent(message.content)}
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-end mb-3">
      <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-tl-sm">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
