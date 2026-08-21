import { useId } from "react";
import { cn } from "@/lib/utils.ts";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import { Checkbox } from "@/components/ui/checkbox.tsx";
import { PermissionEntity } from "@/lib/types.ts";
import { permissionActionName, permissionName } from "@/lib/permission-names.ts";

export type MissingPermission = {
  code: string;
  required_by: string[];
};

export interface PermissionChecklistProps {
  entities: PermissionEntity[];
  selected: string[];
  onChange: (codes: string[]) => void;
  disabled?: boolean;
  missingPermissions?: MissingPermission[];
  className?: string;
}

export function PermissionChecklist({
  entities,
  selected,
  onChange,
  disabled,
  missingPermissions = [],
  className,
}: PermissionChecklistProps) {
  const instanceId = useId();

  const missingByEntity = new Map<string, MissingPermission[]>();
  for (const missing of missingPermissions) {
    const entity = missing.code.split(".")[0];
    missingByEntity.set(entity, [...(missingByEntity.get(entity) ?? []), missing]);
  }

  const toggleCode = (code: string, checked: boolean) => {
    onChange(checked ? [...selected, code] : selected.filter((selectedCode) => selectedCode !== code));
  };

  const toggleEntity = (entityCodes: string[], grantAll: boolean) => {
    const untouched = selected.filter((code) => !entityCodes.includes(code));
    onChange(grantAll ? [...untouched, ...entityCodes] : untouched);
  };

  return (
    <ScrollArea className={cn("h-[280px] w-full rounded-md border px-4 py-2", className)}>
      <div className="space-y-5">
        {entities.map((entity) => {
          const entityCodes = entity.permissions.map((permission) => permission.code);
          const grantedCount = entityCodes.filter((code) => selected.includes(code)).length;
          const entityCheckboxId = `${instanceId}-${entity.entity}`;
          const missing = missingByEntity.get(entity.entity) ?? [];

          return (
            <fieldset key={entity.entity}>
              <legend className="sr-only">{entity.label}</legend>
              <div className="flex items-center space-x-3 border-b pb-1.5 mb-2">
                <Checkbox
                  id={entityCheckboxId}
                  checked={grantedCount === 0
                    ? false
                    : grantedCount === entityCodes.length ? true : "indeterminate"}
                  disabled={disabled}
                  onCheckedChange={(value) => toggleEntity(entityCodes, value !== false)}
                />
                <label htmlFor={entityCheckboxId} className="text-sm font-medium">{entity.label}</label>
              </div>
              <div className="space-y-2">
                {entity.permissions.map((permission) => {
                  const checkboxId = `${instanceId}-${permission.code}`;
                  return (
                    <div key={permission.code} className="flex items-start space-x-3">
                      <Checkbox
                        id={checkboxId}
                        checked={selected.includes(permission.code)}
                        disabled={disabled}
                        onCheckedChange={(value) => toggleCode(permission.code, value === true)}
                        className="mt-0.5"
                      />
                      <label htmlFor={checkboxId} className="flex min-w-0 grow items-baseline gap-3">
                        <span className="text-sm w-24 shrink-0">{permissionActionName(permission.code)}</span>
                        <span className="text-xs text-muted-foreground">{permission.label}</span>
                      </label>
                    </div>
                  );
                })}
              </div>
              {missing.map((entry) => (
                <p key={entry.code} className="text-xs text-destructive mt-1.5">
                  {permissionName(entry.code, entities)} is required by{" "}
                  {entry.required_by.map((code) => permissionName(code, entities)).join(", ")}
                </p>
              ))}
            </fieldset>
          );
        })}
      </div>
    </ScrollArea>
  );
}
