"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  MEDIA_TYPES,
  MEDIA_TYPE_LABELS,
  STATUSES,
  STATUS_LABELS,
  type Item,
  type ItemInput,
  type MediaType,
  type Status,
} from "@/lib/types";

const EMPTY: ItemInput = {
  title: "",
  creator: "",
  media_type: "book",
  status: "planned",
  rating: null,
};

function toInput(item: Item | null): ItemInput {
  if (!item) return EMPTY;
  return {
    title: item.title,
    creator: item.creator,
    media_type: item.media_type,
    status: item.status,
    rating: item.rating,
  };
}

interface ItemFormProps {
  item: Item | null;
  saving: boolean;
  onCancel: () => void;
  onSubmit: (input: ItemInput) => Promise<void>;
}

/** The form body. Mounted only while the dialog is open and keyed by item, so
 *  its state initialises from props once and never needs syncing afterwards. */
function ItemForm({ item, saving, onCancel, onSubmit }: ItemFormProps) {
  const [form, setForm] = useState<ItemInput>(() => toInput(item));

  /** A rating only applies to a finished item, so clear it when the status
   *  moves away from completed. The API enforces this too; doing it here keeps
   *  the user from submitting something we know will be rejected. */
  function handleStatusChange(status: Status) {
    setForm((current) => ({
      ...current,
      status,
      rating: status === "completed" ? current.rating : null,
    }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    await onSubmit({ ...form, title: form.title.trim(), creator: form.creator.trim() });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          required
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="creator">Creator</Label>
        <Input
          id="creator"
          required
          placeholder="Author, director, or studio"
          value={form.creator}
          onChange={(e) => setForm({ ...form, creator: e.target.value })}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>Type</Label>
          <Select
            value={form.media_type}
            onValueChange={(value) => setForm({ ...form, media_type: value as MediaType })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MEDIA_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {MEDIA_TYPE_LABELS[type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label>Status</Label>
          <Select
            value={form.status}
            onValueChange={(value) => handleStatusChange(value as Status)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUSES.map((status) => (
                <SelectItem key={status} value={status}>
                  {STATUS_LABELS[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Only offered once the item is completed, matching the API rule. */}
      {form.status === "completed" && (
        <div className="space-y-1.5">
          <Label>Rating</Label>
          <Select
            value={form.rating === null ? "none" : String(form.rating)}
            onValueChange={(value) =>
              setForm({ ...form, rating: value === "none" ? null : Number(value) })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No rating</SelectItem>
              {[1, 2, 3, 4, 5].map((score) => (
                <SelectItem key={score} value={String(score)}>
                  {"★".repeat(score)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : item ? "Save changes" : "Add item"}
        </Button>
      </DialogFooter>
    </form>
  );
}

interface ItemDialogProps {
  open: boolean;
  /** The item being edited, or null when adding. One dialog serves both so the
   *  form layout and validation live in a single place. */
  item: Item | null;
  saving: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (input: ItemInput) => Promise<void>;
}

export function ItemDialog({
  open,
  item,
  saving,
  onOpenChange,
  onSubmit,
}: ItemDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{item ? "Edit item" : "Add to shelf"}</DialogTitle>
        </DialogHeader>

        {/* The key remounts the form whenever the target changes, so a previous
            edit's values can never leak into the next one. */}
        {open && (
          <ItemForm
            key={item?.id ?? "new"}
            item={item}
            saving={saving}
            onCancel={() => onOpenChange(false)}
            onSubmit={onSubmit}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
