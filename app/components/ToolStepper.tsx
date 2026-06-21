import { ToolCall } from "../types/chat";

interface ToolStepperProps {
  tools: ToolCall[];
}

function getToolDisplay(name: string, args: any) {
  switch (name) {
    case "policy_lookup_tool":
      return {
        title: "Searching Corporate Policies",
        summary: `Querying company guidelines for: "${args.query || ""}"`,
        icon: "🔍"
      };
    case "create_leave_request_tool":
      return {
        title: "Submitting Leave Request",
        summary: `Requesting leave for Employee "${args.employee_id || "N/A"}" from ${args.start_date || "?"} to ${args.end_date || "?"} (Reason: "${args.reason || "None"}")`,
        icon: "📅"
      };
    case "update_crm_opportunity_tool":
      return {
        title: "Updating CRM Opportunity",
        summary: `Setting opportunity "${args.opp_id || "N/A"}" status to "${args.stage || "?"}" (Next step: "${args.next_step || "None"}")`,
        icon: "💼"
      };
    default:
      return {
        title: name.replace(/_/g, " "),
        summary: JSON.stringify(args),
        icon: "⚙️"
      };
  }
}

export default function ToolStepper({ tools }: ToolStepperProps) {
  return (
    <div className="w-full mt-3 pl-4 border-l border-zinc-800 space-y-3">
      <p className="text-[9px] font-mono tracking-widest text-zinc-500 uppercase">
        API Pipeline Steps
      </p>

      {tools.map((tool, idx) => {
        const info = getToolDisplay(tool.name, tool.args);
        
        // Choose status colors and badges
        let statusBg = "bg-zinc-900 border-zinc-800";
        let statusDot = "bg-yellow-500 animate-pulse";
        let statusText = "text-yellow-500";
        let statusLabel = "Running";
        
        if (tool.status === "completed") {
          statusBg = "bg-emerald-950/20 border-emerald-900/30";
          statusDot = "bg-emerald-500";
          statusText = "text-emerald-400";
          statusLabel = "Completed";
        } else if (tool.status === "denied") {
          statusBg = "bg-red-950/20 border-red-900/30";
          statusDot = "bg-red-500";
          statusText = "text-red-400";
          statusLabel = "Access Denied";
        } else if (tool.status === "failed") {
          statusBg = "bg-red-950/20 border-red-900/30";
          statusDot = "bg-red-500";
          statusText = "text-red-400";
          statusLabel = "Failed";
        }

        return (
          <div
            key={idx}
            className={`border rounded-[2px] p-3 transition-colors w-full ${statusBg}`}
          >
            <div className="flex justify-between items-start">
              <div className="flex items-start gap-2.5">
                <span className="text-base mt-0.5">{info.icon}</span>
                <div>
                  <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                    {info.title}
                  </h4>
                  <p className="text-xs text-zinc-400 mt-1 font-sans font-medium">
                    {info.summary}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-1.5 text-[9px] font-mono uppercase">
                <span className={`h-1.5 w-1.5 rounded-full ${statusDot}`} />
                <span className={statusText}>{statusLabel}</span>
              </div>
            </div>

            {/* Collapsible raw logs for developers/auditing */}
            <details className="group mt-3 border-t border-zinc-800/80 pt-2.5">
              <summary className="flex items-center gap-1 text-[9px] font-mono text-zinc-500 hover:text-zinc-300 uppercase tracking-widest cursor-pointer select-none py-0.5">
                <svg
                  className="h-2.5 w-2.5 transition-transform group-open:rotate-90 text-zinc-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M9 5l7 7-7 7" />
                </svg>
                <span>Developer Logs</span>
              </summary>
              
              <div className="mt-2 space-y-2.5 pl-3.5 border-l border-zinc-850 font-mono text-[10px]">
                <div>
                  <span className="text-zinc-500 font-bold uppercase text-[8px] block tracking-wider">Input Arguments</span>
                  <pre className="mt-1 bg-zinc-950/60 p-2 border border-zinc-950 text-zinc-400 overflow-x-auto rounded-[1px]">
                    {JSON.stringify(tool.args, null, 2)}
                  </pre>
                </div>

                {tool.output && (
                  <div className="border-t border-zinc-950 pt-2">
                    <span className="text-zinc-500 font-bold uppercase text-[8px] block tracking-wider">Output Response</span>
                    <pre className={`mt-1 p-2 border overflow-x-auto rounded-[1px] ${
                      tool.status === "denied"
                        ? "bg-red-950/20 border-red-950/40 text-red-400"
                        : "bg-zinc-950/60 border-zinc-950 text-emerald-500/90"
                    }`}>
                      {tool.output}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          </div>
        );
      })}
    </div>
  );
}
