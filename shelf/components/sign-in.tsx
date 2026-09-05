"use client";

import { useState } from "react";
import { toast } from "sonner";

import { useSession } from "@/components/session-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { googleSignInUrl, login, register } from "@/lib/auth";

export function SignIn() {
  const { refresh } = useSession();
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await (isRegistering ? register(email, password) : login(email, password));
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not sign you in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Shelf</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Your books, movies, and games in one place.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            required
            minLength={isRegistering ? 8 : undefined}
            autoComplete={isRegistering ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {isRegistering && (
            <p className="text-xs text-muted-foreground">At least 8 characters.</p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? "Working…" : isRegistering ? "Create account" : "Sign in"}
        </Button>
      </form>

      <div className="my-4 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-xs text-muted-foreground">or</span>
        <span className="h-px flex-1 bg-border" />
      </div>

      {/* A real link, not a fetch: OAuth is a full-page navigation. */}
      <a
        href={googleSignInUrl()}
        className={buttonVariants({ variant: "outline", className: "w-full" })}
      >
        Continue with Google
      </a>

      <button
        type="button"
        className="mt-6 text-sm text-muted-foreground underline underline-offset-4"
        onClick={() => setIsRegistering((v) => !v)}
      >
        {isRegistering
          ? "Already have an account? Sign in"
          : "New here? Create an account"}
      </button>
    </main>
  );
}
