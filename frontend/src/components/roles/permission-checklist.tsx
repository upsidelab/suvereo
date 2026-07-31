import { CheckboxListInput } from "@/components/util/checkbox-list-input.tsx";
import { PermissionOption } from "@/lib/types.ts";

export interface PermissionChecklistProps {
  options: PermissionOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

// manage_X implies view_X, same entity only. Codenames not present in `options` (e.g. the
// dataset-scoped pairs when this checklist is rendered in "global" scope, or vice versa)
// are simply skipped -- one shared table works for both scopes.
const MANAGE_IMPLIES_VIEW: Record<string, string> = {
  "account.manage_users": "account.view_users",
  "account.manage_service_accounts": "account.view_service_accounts",
  "catalog.manage_datasets": "catalog.view_all_datasets",
  "catalog.manage_agents": "catalog.view_dataset",
  "catalog.manage_integrations": "catalog.view_integrations",
};

export function PermissionChecklist({ options, selectedIds, onChange }: PermissionChecklistProps) {
  const byCodename = new Map(options.map((option) => [option.codename, option]));

  const handleChange = (nextIds: number[]) => {
    const currentSet = new Set(selectedIds);
    const nextSet = new Set(nextIds);

    for (const [manageCodename, viewCodename] of Object.entries(MANAGE_IMPLIES_VIEW)) {
      const manageOption = byCodename.get(manageCodename);
      const viewOption = byCodename.get(viewCodename);
      if (!manageOption || !viewOption) continue;

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
      options={options.map((option) => ({ id: option.id, label: option.name }))}
      selectedIds={selectedIds}
      onChange={handleChange}
    />
  );
}
