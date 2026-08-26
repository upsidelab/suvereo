import { PermissionEntity } from "@/lib/permissions/types.ts";
import { permissionName } from "@/lib/permissions/names.ts";

export interface PermissionLabelProps {
  code: string;
  entities: PermissionEntity[];
}

export function PermissionLabel({ code, entities }: PermissionLabelProps) {
  return (
    <span className="rounded-sm font-semibold whitespace-nowrap">
      {permissionName(code, entities)}
    </span>
  );
}
