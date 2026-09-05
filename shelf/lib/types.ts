/** Types mirroring the FastAPI schema, so the UI and API client cannot drift. */

// `as const` gives both a runtime list to render from and a literal union type.
export const MEDIA_TYPES = ["book", "movie", "game"] as const;
export type MediaType = (typeof MEDIA_TYPES)[number];

export const STATUSES = ["planned", "in_progress", "completed"] as const;
export type Status = (typeof STATUSES)[number];

export interface Item {
  id: string;
  title: string;
  creator: string;
  media_type: MediaType;
  status: Status;
  rating: number | null;
  created_at: string;
  updated_at: string;
}

/** Fields the user can set. The server owns id and timestamps. */
export interface ItemInput {
  title: string;
  creator: string;
  media_type: MediaType;
  status: Status;
  rating: number | null;
}

export interface ItemFilters {
  search?: string;
  media_type?: MediaType;
  status?: Status;
}

const MEDIA_TYPE_LABELS: Record<MediaType, string> = {
  book: "Book",
  movie: "Movie",
  game: "Game",
};

const STATUS_LABELS: Record<Status, string> = {
  planned: "Planned",
  in_progress: "In progress",
  completed: "Completed",
};

export interface Option {
  value: string;
  label: string;
}

export const MEDIA_TYPE_OPTIONS: Option[] = MEDIA_TYPES.map((value) => ({
  value,
  label: MEDIA_TYPE_LABELS[value],
}));

export const STATUS_OPTIONS: Option[] = STATUSES.map((value) => ({
  value,
  label: STATUS_LABELS[value],
}));

export const RATING_OPTIONS: Option[] = [1, 2, 3, 4, 5].map((score) => ({
  value: String(score),
  label: "★".repeat(score),
}));

export const mediaTypeLabel = (type: MediaType): string => MEDIA_TYPE_LABELS[type];
export const statusLabel = (status: Status): string => STATUS_LABELS[status];

export interface User {
  id: string;
  email: string;
  created_at: string;
}
