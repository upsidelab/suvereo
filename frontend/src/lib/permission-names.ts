import { PermissionEntity } from "@/lib/types.ts";

/**
 * The action half of a permission code, as the role editor shows it: `dataset.view` reads as
 * "View" under the Dataset heading, `conversation.view_all` as "View all".
 */
export function permissionActionName(code: string): string {
  const action = code.split(".")[1] ?? code;
  const spaced = action.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * A permission named the way the checkboxes are labelled - "Dataset:View" - so an error can be
 * matched against the screen without translating codes. Falls back to the code's own entity when
 * the served entities do not carry it.
 */
export function permissionName(code: string, entities: PermissionEntity[]): string {
  const entityCode = code.split(".")[0];
  const entity = entities.find((candidate) => candidate.entity === entityCode);
  const entityName = entity?.label ?? permissionActionName(`.${entityCode}`);
  return `${entityName}:${permissionActionName(code)}`;
}
