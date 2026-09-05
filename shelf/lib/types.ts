/** Types mirroring the FastAPI schema. Kept in one place so the UI and the
 *  API client cannot drift apart. */

// `as const` arrays give both a runtime list (to render dropdowns from) and a
// literal union type, without writing either one twice.
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

export const STATUS_LABELS: Record<Status, string> = {
  planned: "Planned",
  in_progress: "In progress",
  completed: "Completed",
};

export const MEDIA_TYPE_LABELS: Record<MediaType, string> = {
  book: "Book",
  movie: "Movie",
  game: "Game",
};
