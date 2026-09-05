"use client";

import { useState } from "react";

import { SelectField } from "@/components/select-field";
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
  MEDIA_TYPE_OPTIONS,
  RATING_OPTIONS,
  STATUS_OPTIONS,
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

const NO_RATING = "none";

function toInput(item: Item | null): ItemInput {
  if (!item) return EMPTY;
  const { title, creator, media_type, status, rating } = item;
  return { title, creator, media_type, status, rating };
}

interface ItemFormProps {
  item: Item | null;
  saving: boolean;
  onCancel: () => void;
  onSubmit: (input: ItemInput) => Promise<void>;
}

function ItemForm({ item, saving, onCancel, onSubmit }: ItemFormProps) {
  const [form, setForm] = useState<ItemInput>(() => toInput(item));
  const update = (patch: Partial<ItemInput>) => setForm((f) => ({ ...f, ...patch }));

  // A rating only applies to a finished item, so clear it when the status moves
  // away from completed. The API enforces this too.
  const setStatus = (status: Status) =>
    setForm((f) => ({ ...f, status, rating: status === "completed" ? f.rating : null }));

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
          onChange={(e) => update({ title: e.target.value })}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="creator">Creator</Label>
        <Input
          id="creator"
          required
          placeholder="Author, director, or studio"
          value={form.creator}
          onChange={(e) => update({ creator: e.target.value })}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <SelectField
          label="Type"
          value={form.media_type}
          options={MEDIA_TYPE_OPTIONS}
          onChange={(value) => update({ media_type: value as MediaType })}
        />
        <SelectField
          label="Status"
          value={form.status}
          options={STATUS_OPTIONS}
          onChange={(value) => setStatus(value as Status)}
        />
      </div>

      {form.status === "completed" && (
        <SelectField
          label="Rating"
          value={form.rating === null ? NO_RATING : String(form.rating)}
          options={[{ value: NO_RATING, label: "No rating" }, ...RATING_OPTIONS]}
          onChange={(value) =>
            update({ rating: value === NO_RATING ? null : Number(value) })
          }
        />
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
  /** The item being edited, or null when adding. */
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

        {/* Keyed remount initialises the form from props once, so no effect is
            needed to sync them and no previous edit leaks into the next. */}
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
