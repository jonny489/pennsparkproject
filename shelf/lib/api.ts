import { getSupabase } from "@/lib/supabase";
import type { Item, ItemFilters, ItemInput } from "@/lib/types";

/** Read at call time, not module load, so the app can build without env vars. */
function apiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    throw new Error(
      "Missing NEXT_PUBLIC_API_URL. Copy shelf/.env.example to shelf/.env.local.",
    );
  }
  return base;
}

/** Error carrying the HTTP status so callers can distinguish 401 from 422. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Pull a readable message out of a FastAPI error body.
 *
 *  FastAPI returns `detail` as a string for HTTPException but as an array of
 *  validation objects for a 422, so both shapes have to be handled. */
function extractDetail(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) return fallback;

  const { detail } = body as { detail: unknown };
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) =>
        typeof entry === "object" && entry !== null && "msg" in entry
          ? String((entry as { msg: unknown }).msg)
          : null,
      )
      .filter((msg): msg is string => msg !== null);
    if (messages.length > 0) return messages.join("; ");
  }

  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // The API verifies this token's signature and reads the user id from it, so
  // every request must carry it.
  const { data } = await getSupabase().auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError("You are signed out. Sign in again to continue.", 401);

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });

  if (response.status === 204) return undefined as T;

  // Read the body once; a non-JSON error page must not mask the real status.
  const text = await response.text();
  let parsed: unknown = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = null;
  }

  if (!response.ok) {
    throw new ApiError(
      extractDetail(parsed, `Request failed (${response.status})`),
      response.status,
    );
  }

  return parsed as T;
}

function buildQuery(filters: ItemFilters): string {
  const params = new URLSearchParams();
  // Only send filters that are actually set, so the API applies no-op WHERE
  // clauses for empty values.
  if (filters.search) params.set("search", filters.search);
  if (filters.media_type) params.set("media_type", filters.media_type);
  if (filters.status) params.set("status", filters.status);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const itemsApi = {
  list: (filters: ItemFilters = {}): Promise<Item[]> =>
    request<Item[]>(`/items${buildQuery(filters)}`),

  create: (input: ItemInput): Promise<Item> =>
    request<Item>("/items", { method: "POST", body: JSON.stringify(input) }),

  update: (id: string, input: Partial<ItemInput>): Promise<Item> =>
    request<Item>(`/items/${id}`, { method: "PATCH", body: JSON.stringify(input) }),

  remove: (id: string): Promise<void> =>
    request<void>(`/items/${id}`, { method: "DELETE" }),
};
