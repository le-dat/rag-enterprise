import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserInfo, Message } from "@/types/chat";

interface AppState {
  user: UserInfo | null;
  messages: Message[];
  isLoading: boolean;

  setUser: (user: UserInfo | null) => void;
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  clearMessages: () => void;
  setLoading: (loading: boolean) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      messages: [],
      isLoading: false,

      setUser: (user) => set({ user }),

      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),

      updateMessage: (id, updates) =>
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, ...updates } : m
          ),
        })),

      clearMessages: () => set({ messages: [] }),

      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: "app-storage",
      partialize: (state) => ({ user: state.user }),
    }
  )
);
