import { Message } from "../types/chat";
import ToolStepper from "./ToolStepper";

interface MessageItemProps {
  msg: Message;
}

export default function MessageItem({ msg }: MessageItemProps) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      {/* Stepper for Tool Calls (Rendered ABOVE the message block for better UX) */}
      {!isUser && msg.tools && msg.tools.length > 0 && (
        <ToolStepper tools={msg.tools} />
      )}

      {/* Message block */}
      <div
        className={`max-w-xs rounded-[2px] p-3 md:max-w-3xl md:p-4 font-sans text-sm relative ${
          isUser
            ? "bg-zinc-900 border border-zinc-800 text-zinc-100"
            : "bg-zinc-900/40 border border-zinc-900 text-zinc-200 w-full"
        }`}
      >
        {/* Message Sender Header */}
        <div className="flex justify-between items-center text-[10px] font-mono text-zinc-500 uppercase mb-2 border-b border-zinc-900 pb-1.5 font-semibold">
          <span>{isUser ? "Client" : "Agent Response"}</span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>

        {/* Message content */}
        {msg.content ? (
          <div className="whitespace-pre-wrap leading-relaxed">
            {msg.content}
          </div>
        ) : (
          !msg.blocked && !msg.error && (
            <div className="flex items-center gap-2 py-2">
              <span className="animate-pulse h-2 w-2 bg-emerald-500 rounded-full" />
              <span className="text-xs font-mono text-zinc-500 italic">Thinking...</span>
            </div>
          )
        )}

        {/* Blocked Alert (Input Rail Heuristic) */}
        {msg.blocked && (
          <div className="mt-3 bg-red-950/30 border border-red-800/80 text-red-400 p-3 rounded-[2px] font-mono text-xs flex items-start gap-2.5 animate-shake">
            <span className="text-base">🚨</span>
            <div>
              <p className="font-bold uppercase tracking-wider text-[10px] text-red-300">
                SECURITY RAIL INTERCEPT
              </p>
              <p className="mt-1 text-[11px] leading-relaxed text-red-400/90">
                {msg.blocked.reason}
              </p>
            </div>
          </div>
        )}

        {/* General error message */}
        {msg.error && !msg.blocked && (
          <div className="mt-3 bg-zinc-950 border border-red-950 text-red-400 p-3 rounded-[2px] font-mono text-xs break-all">
            <span className="font-bold">SYSTEM ERROR:</span> {msg.error}
          </div>
        )}

        {/* Fact-check / Grounding check badge */}
        {msg.grounding && msg.role === "assistant" && (
          <div className="mt-4 flex items-center justify-end">
            <div
              className={`flex items-center gap-1.5 text-[9px] font-mono uppercase px-2 py-0.5 border rounded-[1px] ${
                msg.grounding.grounded
                  ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/30"
                  : "bg-red-950/40 text-red-400 border-red-800/30"
              }`}
            >
              <span>{msg.grounding.grounded ? "✓ FACT-CHECKED: GROUNDED" : "✗ FACT-CHECKED: NOT SUPPORTED"}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
