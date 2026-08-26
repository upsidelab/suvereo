import { PERMISSIONS } from "@/lib/permissions/codes.ts";

const ROLE_EDITING_CODES: readonly string[] = [
  PERMISSIONS.GLOBAL_ROLE.ADD,
  PERMISSIONS.GLOBAL_ROLE.CHANGE,
  PERMISSIONS.GLOBAL_ROLE.DELETE,
  PERMISSIONS.DATASET_ROLE.ADD,
  PERMISSIONS.DATASET_ROLE.CHANGE,
  PERMISSIONS.DATASET_ROLE.DELETE,
];

const ROLE_GRANTING_CODES: readonly string[] = [
  PERMISSIONS.GLOBAL_ROLE.ASSIGN,
  PERMISSIONS.DATASET_ROLE.ASSIGN,
];

const ROLE_EDITING_WARNING = "People in this role will be able to edit permission sets, including their own, "
  + "which lets them grant themselves any permission in the system. This is effectively administrator access.";

const ROLE_GRANTING_WARNING = "People in this role will be able to grant roles to anyone, on every data set, "
  + "including to themselves.";

export function permissionEscalationWarnings(submitted: string[], stored: string[]): string[] {
  const alreadyGranted = new Set(stored);
  const added = new Set(submitted.filter((code) => !alreadyGranted.has(code)));
  const warns = (codes: readonly string[]) => codes.some((code) => added.has(code));

  return [
    warns(ROLE_EDITING_CODES) ? ROLE_EDITING_WARNING : null,
    warns(ROLE_GRANTING_CODES) ? ROLE_GRANTING_WARNING : null,
  ].filter((warning): warning is string => warning !== null);
}
