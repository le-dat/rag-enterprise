"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { UserInfo } from "../types/chat";

interface AuthContextType {
  userInfo: UserInfo | null;
  loading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const match = document.cookie.match(new RegExp("(^| )user_info=([^;]*)"));
    if (match) {
      try {
        const decoded = decodeURIComponent(match[2]);
        const parsed = JSON.parse(decoded);
        setUserInfo(parsed);
      } catch (e) {
        console.error("Failed to parse user_info cookie", e);
      }
    }
    setLoading(false);
  }, []);

  const logout = async () => {
    await fetch("/api/auth", { method: "DELETE" });
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ userInfo, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
