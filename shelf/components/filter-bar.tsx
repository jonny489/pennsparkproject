"use client";

import { SelectField } from "@/components/select-field";
import { Input } from "@/components/ui/input";
import {
  MEDIA_TYPE_OPTIONS,
  STATUS_OPTIONS,
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

      <SelectField
        className="sm:w-40"
        value={filters.media_type ?? ALL}
        options={[{ value: ALL, label: "All types" }, ...MEDIA_TYPE_OPTIONS]}
        onChange={(value) =>
          onChange({
            ...filters,
            media_type: value === ALL ? undefined : (value as MediaType),
          })
        }
      />

      <SelectField
        className="sm:w-40"
        value={filters.status ?? ALL}
        options={[{ value: ALL, label: "All statuses" }, ...STATUS_OPTIONS]}
        onChange={(value) =>
          onChange({ ...filters, status: value === ALL ? undefined : (value as Status) })
        }
      />
    </div>
  );
}
