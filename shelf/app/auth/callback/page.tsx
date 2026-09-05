"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { setToken } from "@/lib/auth";

/** Catches the redirect from the API's Google callback. The token arrives in
 *  the URL fragment, which is readable here but never sent to a server. */
export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    if (token) setToken(token);
    // replace, so Back does not return to this page.
    router.replace("/");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-sm text-muted-foreground">Signing you in…</p>
    </main>
  );
}
