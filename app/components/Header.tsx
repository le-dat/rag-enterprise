import { UserInfo } from "../types/chat";

interface HeaderProps {
  userInfo: UserInfo | null;
  onLogout: () => void;
}

export default function Header({ userInfo, onLogout }: HeaderProps) {
  return (
    <header className="border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-md py-5 px-8 relative z-10 flex justify-between items-center">
      <div className="flex items-center gap-3">
        <div className="h-6 w-6 bg-emerald-500 flex justify-center items-center rounded-[2px]">
          <span className="text-lg font-bold text-zinc-950 font-mono">R</span>
        </div>
        <div>
          <h1 className="text-base font-bold font-mono tracking-tight text-white uppercase">
            Enterprise GraphRAG
          </h1>
          <p className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase">
            Secure Pipeline V1
          </p>
        </div>
      </div>

      {userInfo && (
        <div className="flex items-center gap-4">
          {/* Active User Badge */}
          <div className="flex items-center gap-3 border border-zinc-800 bg-zinc-900/60 px-4 py-1.5 rounded-[4px]">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-mono text-zinc-400">
              {userInfo.user_id}
            </span>
            <span className="text-[10px] bg-emerald-950/40 text-emerald-400 px-2 py-0.5 border border-emerald-800/40 font-mono uppercase rounded-[2px]">
              {userInfo.department} · {userInfo.role}
            </span>
          </div>

          <button
            onClick={onLogout}
            className="text-sm font-mono text-zinc-500 hover:text-zinc-300 transition-colors border border-zinc-900 hover:border-zinc-800 bg-zinc-950 px-3 py-1.5 rounded-[4px] cursor-pointer"
          >
            LOGOUT
          </button>
        </div>
      )}
    </header>
  );
}
