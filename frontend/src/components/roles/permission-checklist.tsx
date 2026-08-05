import { CheckboxListInput } from "@/components/util/checkbox-list-input.tsx";
import { PermissionOption } from "@/lib/types.ts";

export interface PermissionChecklistProps {
  options: PermissionOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
}

export function PermissionChecklist({ options, selectedIds, onChange, disabled }: PermissionChecklistProps) {
  const byCodename = new Map(options.map((option) => [option.codename, option]));

  const handleChange = (nextIds: number[]) => {
    const currentSet = new Set(selectedIds);
    const nextSet = new Set(nextIds);

    // manage_X implies view_X. Backend-driven (option.implies), not hardcoded here. An option
    // without an implied pair, or whose implied codename isn't in this scope's options, is
    // simply skipped.
    for (const manageOption of options) {
      if (!manageOption.implies) continue;
      const viewOption = byCodename.get(manageOption.implies);
      if (!viewOption) continue;

      const manageJustChecked = nextSet.has(manageOption.id) && !currentSet.has(manageOption.id);
      if (manageJustChecked) {
        nextSet.add(viewOption.id);
      }

      const manageStillChecked = nextSet.has(manageOption.id);
      const viewJustUnchecked = currentSet.has(viewOption.id) && !nextSet.has(viewOption.id);
      if (manageStillChecked && viewJustUnchecked) {
        nextSet.add(viewOption.id);
      }
    }

    onChange(Array.from(nextSet));
  };

  return (
    <CheckboxListInput
      options={options.map((option) => ({ id: option.id, label: option.name, description: option.description }))}
      selectedIds={selectedIds}
      onChange={handleChange}
      disabled={disabled}
    />
  );
}
