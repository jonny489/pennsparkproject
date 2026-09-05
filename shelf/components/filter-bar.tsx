"use client";

import { Input } from "@/components/ui/input";
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
  type ItemFilters,
  type MediaType,
  type Status,
} from "@/lib/types";

// Radix Select has no empty-string value, so "all" stands in for "no filter"
// and is translated back to undefined before it reaches the API.
const ALL = "all";

interface FilterBarProps {
  filters: ItemFilters;
  onChange: (filters: ItemFilters) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row">
      <Input
        placeholder="Search titles…"
        className="sm:max-w-xs"
        value={filters.search ?? ""}
        onChange={(e) => onChange({ ...filters, search: e.target.value || undefined })}
      />

      <Select
        value={filters.media_type ?? ALL}
        onValueChange={(value) =>
          onChange({
            ...filters,
            media_type: value === ALL ? undefined : (value as MediaType),
          })
        }
      >
        <SelectTrigger className="sm:w-40">
          <SelectValue placeholder="All types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>All types</SelectItem>
          {MEDIA_TYPES.map((type) => (
            <SelectItem key={type} value={type}>
              {MEDIA_TYPE_LABELS[type]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.status ?? ALL}
        onValueChange={(value) =>
          onChange({ ...filters, status: value === ALL ? undefined : (value as Status) })
        }
      >
        <SelectTrigger className="sm:w-40">
          <SelectValue placeholder="All statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>All statuses</SelectItem>
          {STATUSES.map((status) => (
            <SelectItem key={status} value={status}>
              {STATUS_LABELS[status]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
