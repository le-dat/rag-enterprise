import React from "react";

interface ChatInputProps {
  inputValue: string;
  setInputValue: (val: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
  sessionId: string;
}

export default function ChatInput({
  inputValue,
  setInputValue,
  onSubmit,
  loading,
  sessionId,
}: ChatInputProps) {
  return (
    <footer className="border-t border-zinc-900 bg-zinc-950/90 py-3 px-3 md:py-4 md:px-6 relative z-10">
      <form onSubmit={onSubmit} className="max-w-xs mx-auto flex gap-2 md:max-w-4xl md:gap-3">
        <input
          type="text"
          placeholder="Type your message here..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={loading}
          className="flex-1 bg-zinc-900 border border-zinc-800 rounded-[2px] px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-sans"
        />
        <button
          type="submit"
          disabled={loading || !inputValue.trim()}
          className="bg-emerald-500 hover:bg-emerald-600 disabled:bg-zinc-900 disabled:text-zinc-600 text-zinc-950 font-mono text-xs font-bold tracking-widest px-3 md:px-6 rounded-[2px] transition-colors cursor-pointer flex items-center justify-center"
        >
          SEND
        </button>
      </form>
      <div className="max-w-xs mx-auto mt-1 md:max-w-4xl md:mt-2 flex justify-between items-center text-[9px] font-mono text-zinc-500 px-1">
        <span>SSE DATA STREAM</span>
        <span>SESSION ID: {sessionId}</span>
      </div>
    </footer>
  );
}
