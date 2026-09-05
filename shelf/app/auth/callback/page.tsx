"use client";

import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

import { setToken } from "@/lib/auth";

const MESSAGES: Record<string, string> = {
  cancelled: "Sign-in was cancelled.",
  exchange_failed: "Google sign-in failed. Please try again.",
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
  const hash = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const params = new URLSearchParams(hash.slice(1));
  const token = params.get("token");
  const reason = params.get("error");
  const error = reason
    ? (MESSAGES[reason] ?? "Google sign-in failed. Please try again.")
    : null;

  useEffect(() => {
    if (!token) return;
    setToken(token);
    // replace, so Back does not return to this page.
    router.replace("/");
  }, [token, router]);

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
