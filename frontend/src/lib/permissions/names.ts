import { PermissionEntity } from "@/lib/permissions/types.ts";


export function permissionActionName(code: string): string {
  const action = code.split(".")[1] ?? code;
  return action
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function permissionName(code: string, entities: PermissionEntity[]): string {
  const entityCode = code.split(".")[0];
  const entity = entities.find((candidate) => candidate.entity === entityCode);
  const entityName = entity?.label ?? permissionActionName(`.${entityCode}`);
  return `${entityName}:${permissionActionName(code)}`;
}
