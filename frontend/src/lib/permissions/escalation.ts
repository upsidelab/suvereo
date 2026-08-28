import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { EscalationWarning } from "@/lib/permissions/types.ts";

const ROLE_ADD_CODES: readonly string[] = [PERMISSIONS.GLOBAL_ROLE.ADD, PERMISSIONS.DATASET_ROLE.ADD];
const ROLE_EDIT_CODES: readonly string[] = [PERMISSIONS.GLOBAL_ROLE.CHANGE, PERMISSIONS.DATASET_ROLE.CHANGE];
const ROLE_ASSIGN_CODES: readonly string[] = [
  PERMISSIONS.GLOBAL_ROLE.ASSIGN,
  PERMISSIONS.DATASET_ROLE.ASSIGN,
  PERMISSIONS.GROUP.ASSIGN,
];

const ADD_WARNING = "People in this role will be able to create roles carrying any permission in the system, "
  + "including a role that amounts to administrator access.";

const EDIT_WARNING = "People in this role will be able to edit permission sets, including those of roles they "
  + "hold themselves. Nothing stops them granting themselves every permission in the system, so anyone holding "
  + "this role can self-promote to an effective administrator.";

const ASSIGN_WARNING = "People in this role will be able to grant roles to anyone, including to themselves, and to hand out whatever a group holds by adding members to it.";

function warningsFor(permissions: Set<string>): EscalationWarning[] {
  const carried = (codes: readonly string[]) => codes.filter((code) => permissions.has(code));

  const edit = carried(ROLE_EDIT_CODES);
  const add = carried(ROLE_ADD_CODES);
  const assign = carried(ROLE_ASSIGN_CODES);

  const warnings: EscalationWarning[] = [];
  if (edit.length > 0) {
    warnings.push({ message: EDIT_WARNING, codes: edit });
  } else if (add.length > 0) {
    warnings.push({ message: ADD_WARNING, codes: add });
  }
  if (assign.length > 0) {
    warnings.push({ message: ASSIGN_WARNING, codes: assign });
  }
  return warnings;
}

export function permissionEscalationWarnings(submitted: string[], stored: string[]): EscalationWarning[] {
  const warnings = warningsFor(new Set(submitted));
  const alreadyWarned = new Map(
    warningsFor(new Set(stored)).map((warning) => [warning.message, new Set(warning.codes)]),
  );

  const isNew = (warning: EscalationWarning) => {
    const covered = alreadyWarned.get(warning.message);
    return covered === undefined || warning.codes.some((code) => !covered.has(code));
  };

  return warnings.some(isNew) ? warnings : [];
}
