"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";

import { useSession } from "@/components/session-provider";
import { setToken } from "@/lib/auth";

const GENERIC_ERROR = "Google sign-in failed. Please try again.";

const MESSAGES: Record<string, string> = {
  cancelled: "Sign-in was cancelled.",
  exchange_failed: GENERIC_ERROR,
  email_taken:
    "That email already has a password account. Sign in with your password instead.",
};

// The hash is external, non-React data that never changes after mount. Reading
// it this way avoids both an effect-and-setState round trip and a hydration
// mismatch — the server snapshot is empty, the client's is the real hash.
const subscribe = () => () => {};
const getSnapshot = () => window.location.hash;
const getServerSnapshot = () => "";

/** Catches the redirect from the API's Google callback. The token arrives in
 *  the URL fragment, which is readable here but never sent to a server. */
export default function AuthCallback() {
  const router = useRouter();
  const { refresh } = useSession();
  const [refreshFailed, setRefreshFailed] = useState(false);
  const hash = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const params = new URLSearchParams(hash.slice(1));
  const token = params.get("token");
  const reason = params.get("error");
  const error = reason
    ? (MESSAGES[reason] ?? GENERIC_ERROR)
    : refreshFailed
      ? GENERIC_ERROR
      : null;

  useEffect(() => {
    if (!token) return;
    setToken(token);

    let active = true;
    // The provider already resolved the session — as "signed out", because the
    // hash is only readable after hydration, so the token landed after its one
    // mount effect had run. Without this re-read, "/" renders the sign-in form
    // despite a perfectly good token sitting in localStorage.
    refresh().then(
      () => {
        // replace, so Back does not return to this page.
        if (active) router.replace("/");
      },
      () => {
        if (active) setRefreshFailed(true);
      },
    );
    return () => {
      active = false;
    };
  }, [token, refresh, router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center gap-4 px-6 text-center">
      {error ? (
        <>
          <p className="text-sm text-destructive">{error}</p>
          <button
            type="button"
            className="text-sm underline underline-offset-4"
            onClick={() => router.replace("/")}
          >
            Back to sign in
          </button>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Signing you in…</p>
      )}
    </main>
  );
}
