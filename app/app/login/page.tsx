"use client";

import { useState, useEffect } from "react";

export default function LoginPage() {
  const [role, setRole] = useState("staff");
  const [department, setDepartment] = useState("HR");
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Redirect to home if already logged in
  useEffect(() => {
    const match = document.cookie.match(new RegExp("(^| )user_info=([^;]*)"));
    if (match) {
      window.location.href = "/";
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/api/auth", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          role,
          department,
          user_id: userId.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to authenticate.");
      }

      // Successful login, redirect to chat interface
      window.location.href = "/";
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen w-full bg-zinc-950 text-zinc-100 flex flex-col justify-center items-center p-6 relative overflow-hidden">
      {/* Background Matrix/Cyber grid effect */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />

      {/* Cyber Glow Accent */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-emerald-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-emerald-500/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-[2px] p-8 relative z-10 shadow-2xl">
        {/* Top Status Header */}
        <div className="flex justify-between items-center mb-6 border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] tracking-[0.2em] font-mono text-zinc-400 uppercase">
              SYS_PORTAL_V1
            </span>
          </div>
          <span className="text-[10px] font-mono text-emerald-500 uppercase bg-emerald-950/40 px-2 py-0.5 border border-emerald-800/50 rounded-[1px]">
            SECURE ACCESS
          </span>
        </div>

        <div className="mb-8">
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white mb-2">
            ENTERPRISE RAG
          </h1>
          <p className="text-xs text-zinc-400 font-sans">
            Authentication Gate: Select your role and department context to generate a signed JWT.
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-950/40 border border-red-800/80 rounded-[2px] p-3 text-xs font-mono text-red-400 flex items-start gap-2">
            <span className="font-bold">🚨 ERROR:</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* User ID Input (Optional) */}
          <div className="space-y-2">
            <label className="block text-xs font-mono tracking-wide text-zinc-400 uppercase">
              User ID <span className="text-zinc-600">(Optional)</span>
            </label>
            <input
              type="text"
              placeholder="e.g. emp_sales_01 (Auto-generated if empty)"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-[2px] px-3 py-2 text-sm text-zinc-100 font-mono focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
            />
          </div>

          {/* Department Selection */}
          <div className="space-y-2">
            <label className="block text-xs font-mono tracking-wide text-zinc-400 uppercase">
              Department Context (RBAC)
            </label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { value: "HR", label: "HR Department" },
                { value: "Sales", label: "Sales Department" },
              ].map((dept) => (
                <button
                  key={dept.value}
                  type="button"
                  onClick={() => setDepartment(dept.value)}
                  className={`py-2 px-3 border rounded-[2px] text-xs font-mono tracking-wider transition-all duration-200 text-center ${
                    department === dept.value
                      ? "bg-emerald-950/30 border-emerald-500 text-emerald-400 font-bold"
                      : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                  }`}
                >
                  {dept.label}
                </button>
              ))}
            </div>
          </div>

          {/* Role Selection */}
          <div className="space-y-2">
            <label className="block text-xs font-mono tracking-wide text-zinc-400 uppercase">
              Role Authority Level (RBAC)
            </label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { value: "manager", label: "Manager" },
                { value: "staff", label: "Staff / Employee" },
              ].map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setRole(r.value)}
                  className={`py-2 px-3 border rounded-[2px] text-xs font-mono tracking-wider transition-all duration-200 text-center ${
                    role === r.value
                      ? "bg-emerald-950/30 border-emerald-500 text-emerald-400 font-bold"
                      : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-emerald-500 hover:bg-emerald-600 disabled:bg-zinc-800 disabled:text-zinc-600 text-zinc-950 font-mono text-sm font-bold tracking-wider py-2.5 px-4 rounded-[2px] transition-colors duration-200 cursor-pointer flex justify-center items-center gap-2"
          >
            {loading ? (
              <>
                <span className="animate-spin h-4 w-4 border-2 border-zinc-950 border-t-transparent rounded-full" />
                SECURE AUTHENTICATING...
              </>
            ) : (
              "AUTHENTICATE & ENTER"
            )}
          </button>
        </form>

        {/* Footer Info */}
        <div className="mt-8 border-t border-zinc-800/80 pt-4 flex justify-between items-center text-[9px] font-mono text-zinc-500">
          <span>SECURE PROTOCOL SHA-256</span>
          <span>ENTERPRISE COMPLIANT</span>
        </div>
      </div>
    </main>
  );
}
