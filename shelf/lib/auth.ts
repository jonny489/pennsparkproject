import type { User } from "@/lib/types";

const TOKEN_KEY = "shelf.token";

/** Read at call time, not module load, so the app builds without env vars. */
export function apiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    throw new Error(
      "Missing NEXT_PUBLIC_API_URL. Copy shelf/.env.example to shelf/.env.local.",
    );
  }
  return base;
}

// localStorage throws in some privacy modes, so every access is guarded.
export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // A session that cannot be persisted still works until the tab closes.
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing stored, nothing to remove.
  }
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

async function post(path: string, body: unknown): Promise<TokenResponse> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = parsed?.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Something went wrong. Try again.",
    );
  }
  return parsed as TokenResponse;
}

export async function register(email: string, password: string): Promise<User> {
  const result = await post("/auth/register", { email, password });
  setToken(result.access_token);
  return result.user;
}

export async function login(email: string, password: string): Promise<User> {
  const result = await post("/auth/login", { email, password });
  setToken(result.access_token);
  return result.user;
}

/** Null when the stored token is missing, expired, or rejected. */
export async function fetchMe(): Promise<User | null> {
  const token = getToken();
  if (!token) return null;

  const response = await fetch(`${apiBaseUrl()}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    clearToken();
    return null;
  }
  return (await response.json()) as User;
}

export const googleSignInUrl = (): string => `${apiBaseUrl()}/auth/google`;
