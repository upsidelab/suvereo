import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import { CheckboxListInput } from "@/components/util/checkbox-list-input.tsx";
import { PermissionEntity } from "@/lib/types.ts";
import { PERMISSIONS } from "@/lib/permissions.ts";

export type MissingPermission = {
  code: string;
  required_by: string[];
};

const CODE_NOTES: Record<string, string> = {
  [PERMISSIONS.GROUP.ASSIGN]:
    "Grants the ability to place any user in any existing group. Also grant User → View, or the member picker will have nothing to list.",
  [PERMISSIONS.DATASET_ROLE.ASSIGN]:
    "Also grant User → View, or the member picker will have nothing to list.",
};

export interface PermissionChecklistProps {
  entities: PermissionEntity[];
  selected: string[];
  onChange: (codes: string[]) => void;
  disabled?: boolean;
  missingPermissions?: MissingPermission[];
}

export function PermissionChecklist({
  entities,
  selected,
  onChange,
  disabled,
  missingPermissions = [],
}: PermissionChecklistProps) {
  const missingByEntity = new Map<string, MissingPermission[]>();
  for (const missing of missingPermissions) {
    const entity = missing.code.split(".")[0];
    missingByEntity.set(entity, [...(missingByEntity.get(entity) ?? []), missing]);
  }

  const toggle = (entityCodes: string[]) => (codes: string[]) => {
    const untouched = selected.filter((code) => !entityCodes.includes(code));
    onChange([...untouched, ...codes]);
  };

  return (
    <ScrollArea className="h-[280px] w-full rounded-md border px-4 py-2">
      <div className="space-y-4">
        {entities.map((entity) => {
          const entityCodes = entity.permissions.map((permission) => permission.code);
          const missing = missingByEntity.get(entity.entity) ?? [];
          return (
            <fieldset key={entity.entity}>
              <legend className="text-sm font-medium mb-2">{entity.label}</legend>
              <CheckboxListInput
                options={entity.permissions.map((permission) => ({
                  code: permission.code,
                  label: permission.label,
                  note: CODE_NOTES[permission.code],
                }))}
                selectedCodes={selected.filter((code) => entityCodes.includes(code))}
                onChange={toggle(entityCodes)}
                disabled={disabled}
              />
              {missing.map((entry) => (
                <p key={entry.code} className="text-xs text-destructive mt-1">
                  {entry.code} is required by {entry.required_by.join(", ")}
                </p>
              ))}
            </fieldset>
          );
        })}
      </div>
    </ScrollArea>
  );
}
