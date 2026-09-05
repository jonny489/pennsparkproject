"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { clearToken, fetchMe } from "@/lib/auth";
import type { User } from "@/lib/types";

interface SessionState {
  user: User | null;
  /** True until the first /auth/me call resolves, so the sign-in screen does
   *  not flash at an already-signed-in user. */
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => void;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const applyUser = useCallback((next: User | null) => {
    setUser(next);
    setLoading(false);
  }, []);

  /** Re-read the session after a sign-in. Called from event handlers, never
   *  from an effect. */
  const refresh = useCallback(async () => {
    applyUser(await fetchMe());
  }, [applyUser]);

  useEffect(() => {
    let active = true;
    // setState lives in the callback rather than the effect body, and the guard
    // stops an update landing after the provider unmounts.
    void fetchMe().then((next) => {
      if (active) applyUser(next);
    });
    return () => {
      active = false;
    };
  }, [applyUser]);

  const value = useMemo<SessionState>(
    () => ({
      user,
      loading,
      refresh,
      signOut: () => {
        clearToken();
        setUser(null);
      },
    }),
    [user, loading, refresh],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside a SessionProvider");
  return context;
}
