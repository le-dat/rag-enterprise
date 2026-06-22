"use client";

import { useState, useEffect, useRef } from "react";
import { Message } from "../types/chat";
import Header from "../components/Header";
import WelcomeBanner from "../components/WelcomeBanner";
import MessageItem from "../components/MessageItem";
import ChatInput from "../components/ChatInput";
import { useAuth } from "../contexts/AuthContext";

export default function Home() {
  const { userInfo, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load session ID on mount
  useEffect(() => {
    // Generate a simple unique session ID if not set
    let storedSessionId = localStorage.getItem("rag_session_id");
    if (!storedSessionId) {
      storedSessionId = `sess_${Math.random().toString(36).substring(2, 10)}`;
      localStorage.setItem("rag_session_id", storedSessionId);
    }
    setSessionId(storedSessionId);
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleLogout = async () => {
    await logout();
  };

  const handleSuggest = (text: string) => {
    setInputValue(text);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || loading) return;

    const queryText = inputValue;
    setInputValue("");
    setLoading(true);

    const userMessageId = `user_${Date.now()}`;
    const assistantMessageId = `assistant_${Date.now()}`;

    // Add user message
    const newUserMsg: Message = {
      id: userMessageId,
      role: "user",
      content: queryText,
    };
    setMessages((prev) => [...prev, newUserMsg]);

    // Create placeholder assistant message
    const newAssistantMsg: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      tools: [],
    };
    setMessages((prev) => [...prev, newAssistantMsg]);

    try {
      const response = await fetch("/api/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: queryText,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errDetail = errorData.error || "Request failed";
        
        // Check if query was blocked by security (Input Rail)
        if (response.status === 400 && errDetail.toLowerCase().includes("blocked by security")) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    blocked: {
                      type: "input_rail",
                      reason: errDetail,
                    },
                    content: "Security Shield Intercepted: This request violates company safety guidelines.",
                  }
                : msg
            )
          );
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, error: errDetail, content: "Failed to query backend." }
                : msg
            )
          );
        }
        setLoading(false);
        return;
      }

      // Read SSE stream
      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body stream");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const jsonStr = trimmed.slice(6).trim();
            if (jsonStr === "[DONE]" || jsonStr === '{"event": "done"}') {
              continue;
            }

            try {
              const data = JSON.parse(jsonStr);
              
              if (data.event === "token") {
                // Stream text
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: msg.content + data.text }
                      : msg
                  )
                );
              } else if (data.event === "tool_start") {
                // Tool calling started
                setMessages((prev) =>
                  prev.map((msg) => {
                    if (msg.id === assistantMessageId) {
                      const newTools = [...(msg.tools || [])];
                      newTools.push({
                        name: data.tool,
                        args: data.args,
                        status: "running",
                      });
                      return { ...msg, tools: newTools };
                    }
                    return msg;
                  })
                );
              } else if (data.event === "tool_end") {
                // Tool completed
                let toolOutput = data.output;
                let isDenied = toolOutput.includes("Access Denied") || toolOutput.includes("denied");
                let groundingVal: { grounded: boolean; reason?: string } | undefined = undefined;

                try {
                  const parsed = JSON.parse(toolOutput);
                  if (parsed.status === "denied") {
                    isDenied = true;
                  }
                  if (parsed.grounding !== undefined) {
                    groundingVal = {
                      grounded: parsed.grounding,
                      reason: parsed.reason || "Cross-checked with parsed source document chunks."
                    };
                  }
                  // Choose user-friendly formatted output for display
                  if (parsed.reason && parsed.status === "denied") {
                    toolOutput = parsed.reason;
                  } else if (parsed.raw_output) {
                    toolOutput = parsed.raw_output;
                  } else if (parsed.message) {
                    toolOutput = parsed.message;
                  }
                } catch (e) {
                  // Legacy string matches
                  if (data.tool === "policy_lookup_tool") {
                    const matchGrounded = toolOutput.match(/\[Grounding Status: (True|False)\]/);
                    if (matchGrounded) {
                      groundingVal = {
                        grounded: matchGrounded[1] === "True",
                        reason: "Cross-checked with parsed source document chunks."
                      };
                    }
                  }
                }

                setMessages((prev) =>
                  prev.map((msg) => {
                    if (msg.id === assistantMessageId) {
                      const newTools = (msg.tools || []).map((t) => {
                        if (t.name === data.tool && t.status === "running") {
                          return {
                            ...t,
                            status: (isDenied ? "denied" : "completed") as any,
                            output: toolOutput,
                          };
                        }
                        return t;
                      });
                      return {
                        ...msg,
                        tools: newTools,
                        grounding: groundingVal || msg.grounding
                      };
                    }
                    return msg;
                  })
                );
              } else if (data.event === "error") {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, error: data.message }
                      : msg
                  )
                );
              }
            } catch (e) {
              console.error("SSE line parse error:", e, jsonStr);
            }
          }
        }
      }
    } catch (err: any) {
      console.error(err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, error: err.message || "Network stream error", content: "Steam disconnection occurred." }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="h-screen overflow-hidden w-full bg-zinc-950 text-zinc-100 flex flex-col relative font-sans">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#18181b_1px,transparent_1px),linear-gradient(to_bottom,#18181b_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

      {/* Top Navbar */}
      <Header userInfo={userInfo} onLogout={handleLogout} />

      {/* Chat Area */}
      <section className="flex-1 w-full max-w-xs mx-auto md:max-w-4xl flex flex-col p-3 md:p-6 relative z-10 overflow-hidden">
        <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2 space-y-6 scrollbar-thin scrollbar-thumb-zinc-800">
          {messages.length === 0 ? (
            <WelcomeBanner onSelectSuggestion={handleSuggest} />
          ) : (
            messages.map((msg) => (
              <MessageItem key={msg.id} msg={msg} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </section>

      {/* Input Form Bar */}
      <ChatInput
        inputValue={inputValue}
        setInputValue={setInputValue}
        onSubmit={handleSubmit}
        loading={loading}
        sessionId={sessionId}
      />
    </main>
  );
}
