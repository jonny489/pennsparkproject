"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Option } from "@/lib/types";

interface SelectFieldProps {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  className?: string;
}

/** A labelled select. Exists because the dialog and the filter bar would
 *  otherwise repeat the same six-element Radix structure five times over. */
export function SelectField({
  value,
  options,
  onChange,
  label,
  placeholder,
  className,
}: SelectFieldProps) {
  // Radix reports null when a selection is cleared. These selects always hold
  // a value, so ignore that rather than widening every caller's handler.
  const handleChange = (next: string | null) => {
    if (next !== null) onChange(next);
  };

  const select = (
    <Select value={value} onValueChange={handleChange}>
      <SelectTrigger className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  if (!label) return select;
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {select}
    </div>
  );
}
