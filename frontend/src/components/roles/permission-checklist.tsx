import { CheckboxListInput } from "@/components/util/checkbox-list-input.tsx";
import { PermissionOption } from "@/lib/types.ts";

export interface PermissionChecklistProps {
  options: PermissionOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

export function PermissionChecklist({ options, selectedIds, onChange }: PermissionChecklistProps) {
  return (
    <CheckboxListInput
      options={options.map((option) => ({ id: option.id, label: option.name }))}
      selectedIds={selectedIds}
      onChange={onChange}
    />
  );
}
