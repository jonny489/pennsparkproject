"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { FilterBar } from "@/components/filter-bar";
import { ItemCard } from "@/components/item-card";
import { ItemDialog } from "@/components/item-dialog";
import { useSession } from "@/components/session-provider";
import { Button } from "@/components/ui/button";
import { ApiError, itemsApi } from "@/lib/api";
import type { Item, ItemFilters, ItemInput } from "@/lib/types";

/** Wait this long after the last keystroke, so typing a search term costs one
 *  request rather than one per character. */
const SEARCH_DEBOUNCE_MS = 300;

const message = (error: unknown, fallback: string) =>
  error instanceof ApiError ? error.message : fallback;

export function Collection() {
  const { user, signOut } = useSession();

  const [items, setItems] = useState<Item[]>([]);
  const [filters, setFilters] = useState<ItemFilters>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Item | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (active: ItemFilters) => {
    setLoading(true);
    setLoadError(null);
    try {
      setItems(await itemsApi.list(active));
    } catch (error) {
      // Show the failure rather than an empty shelf, which would wrongly read
      // as "you have no items".
      setLoadError(message(error, "Could not load your collection."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => void load(filters), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [filters, load]);

  function openDialog(item: Item | null) {
    setEditing(item);
    setDialogOpen(true);
  }

  async function handleSubmit(input: ItemInput) {
    setSaving(true);
    try {
      if (editing) {
        await itemsApi.update(editing.id, input);
        toast.success("Item updated");
      } else {
        await itemsApi.create(input);
        toast.success("Added to your shelf");
      }
      setDialogOpen(false);
      await load(filters);
    } catch (error) {
      toast.error(message(error, "Could not save this item."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: Item) {
    if (!window.confirm(`Remove "${item.title}" from your shelf?`)) return;
    try {
      await itemsApi.remove(item.id);
      toast.success("Item removed");
      await load(filters);
    } catch (error) {
      toast.error(message(error, "Could not remove this item."));
    }
  }

  const hasFilters = Boolean(filters.search || filters.media_type || filters.status);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Shelf</h1>
          <p className="text-sm text-muted-foreground">{user?.email}</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => openDialog(null)}>Add item</Button>
          <Button variant="ghost" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </header>

      <div className="mt-6">
        <FilterBar filters={filters} onChange={setFilters} />
      </div>

      <section className="mt-6">
        {loading ? (
          <p className="py-12 text-center text-sm text-muted-foreground">Loading…</p>
        ) : loadError ? (
          <div className="py-12 text-center">
            <p className="text-sm text-destructive">{loadError}</p>
            <Button variant="outline" className="mt-3" onClick={() => void load(filters)}>
              Try again
            </Button>
          </div>
        ) : items.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            {hasFilters
              ? "Nothing matches those filters."
              : "Your shelf is empty. Add your first book, movie, or game."}
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                onEdit={openDialog}
                onDelete={(target) => void handleDelete(target)}
              />
            ))}
          </div>
        )}
      </section>

      <ItemDialog
        open={dialogOpen}
        item={editing}
        saving={saving}
        onOpenChange={setDialogOpen}
        onSubmit={handleSubmit}
      />
    </main>
  );
}
