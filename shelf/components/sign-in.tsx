"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getSupabase } from "@/lib/supabase";

/** Magic-link sign-in. No password to store, reset, or leak. */
export function SignIn() {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSending(true);

    const { error } = await getSupabase().auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });

    setSending(false);

    // Surface the real reason rather than failing silently.
    if (error) {
      toast.error(error.message);
      return;
    }
    setSent(true);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Shelf</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Your books, movies, and games in one place.
      </p>

      {sent ? (
        <p className="mt-8 rounded-md border bg-muted/40 p-4 text-sm">
          Check <span className="font-medium">{email}</span> for a sign-in link.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <Button type="submit" className="w-full" disabled={sending}>
            {sending ? "Sending…" : "Send sign-in link"}
          </Button>
        </form>
      )}
    </main>
  );
}
