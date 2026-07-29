import { Checkbox } from "@/components/ui/checkbox.tsx";
import { PermissionOption } from "@/lib/types.ts";

export interface PermissionChecklistProps {
  options: PermissionOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

export function PermissionChecklist({ options, selectedIds, onChange }: PermissionChecklistProps) {
  return (
    <div className="space-y-2">
      {options.map((option) => {
        const checked = selectedIds.includes(option.id);
        return (
          <div key={option.id} className="flex items-center space-x-2">
            <Checkbox
              id={`permission-${option.id}`}
              checked={checked}
              onCheckedChange={(value) => {
                onChange(value ? [...selectedIds, option.id] : selectedIds.filter((id) => id !== option.id));
              }}
            />
            <label htmlFor={`permission-${option.id}`} className="text-sm">{option.name}</label>
          </div>
        );
      })}
    </div>
  );
}
