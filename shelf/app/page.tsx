"use client";

import { Collection } from "@/components/collection";
import { useSession } from "@/components/session-provider";
import { SignIn } from "@/components/sign-in";

export default function Home() {
  const { session, loading } = useSession();

  // Hold the page blank until the session resolves, so an already-signed-in
  // user never sees the sign-in form flash.
  if (loading) return null;

  return session ? <Collection /> : <SignIn />;
}
