import { apiBaseUrl, getToken } from "@/lib/auth";
import type { Item, ItemFilters, ItemInput } from "@/lib/types";

/** Error carrying the HTTP status, so callers can tell 401 from 422. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** FastAPI sends `detail` as a string for an HTTPException but as an array of
 *  validation objects for a 422, so both shapes have to be handled. */
function extractDetail(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) return fallback;

  const { detail } = body as { detail: unknown };
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return fallback;

  const messages = detail.flatMap((entry) =>
    typeof entry === "object" && entry !== null && "msg" in entry
      ? [String((entry as { msg: unknown }).msg)]
      : [],
  );
  return messages.length > 0 ? messages.join("; ") : fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // The API reads the user id out of this token, so every request carries it.
  const token = getToken();
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

function buildQuery({ search, media_type, status }: ItemFilters): string {
  // Only send filters that are set, so the API applies no empty WHERE clauses.
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (media_type) params.set("media_type", media_type);
  if (status) params.set("status", status);
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
