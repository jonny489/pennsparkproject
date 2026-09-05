"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { mediaTypeLabel, statusLabel, type Item } from "@/lib/types";

interface ItemCardProps {
  item: Item;
  onEdit: (item: Item) => void;
  onDelete: (item: Item) => void;
}

export function ItemCard({ item, onEdit, onDelete }: ItemCardProps) {
  return (
    <Card className="flex flex-col justify-between">
      <CardContent className="space-y-3">
        <div>
          <h3 className="font-medium leading-tight">{item.title}</h3>
          <p className="mt-0.5 text-sm text-muted-foreground">{item.creator}</p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary">{mediaTypeLabel(item.media_type)}</Badge>
          <Badge variant={item.status === "completed" ? "default" : "outline"}>
            {statusLabel(item.status)}
          </Badge>
          {item.rating !== null && (
            <span
              className="text-sm text-amber-500"
              aria-label={`Rated ${item.rating} out of 5`}
            >
              {"★".repeat(item.rating)}
            </span>
          )}
        </div>

        <div className="flex gap-2 pt-1">
          <Button size="sm" variant="outline" onClick={() => onEdit(item)}>
            Edit
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onDelete(item)}>
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
