import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { EscalationRisk } from "@/lib/permissions/types.ts";


const ESCALATION_RISKS: Record<string, string> = {
  [PERMISSIONS.GLOBAL_ROLE.ADD]:
    "Create global roles carrying any permission in the system, including one equivalent to an administrator.",
  [PERMISSIONS.GLOBAL_ROLE.CHANGE]:
    "Edit any global role's permissions, including one they hold themselves - a direct route to "
    + "granting themselves full access.",
  [PERMISSIONS.GLOBAL_ROLE.ASSIGN]:
    "Grant any global role to any user, service account or group, their own account included.",
  [PERMISSIONS.DATA_SET_ROLE.ADD]:
    "Create data set roles carrying any permission available on a data set.",
  [PERMISSIONS.DATA_SET_ROLE.CHANGE]:
    "Change the permissions on any data set role, including roles they hold themselves.",
  [PERMISSIONS.DATA_SET_ROLE.ASSIGN]:
    "Grant any data set role, on any data set, to any user, service account or group.",
  [PERMISSIONS.GROUP.ASSIGN]:
    "Add anyone to any group, handing them every role that group already holds.",
};

function risksIn(permissions: string[]): string[] {
  const held = new Set(permissions);
  return Object.keys(ESCALATION_RISKS).filter((code) => held.has(code));
}

export function permissionEscalationRisks(submitted: string[], stored: string[]): EscalationRisk[] {
  const submittedRisks = risksIn(submitted);
  const storedRisks = new Set(risksIn(stored));

  if (!submittedRisks.some((code) => !storedRisks.has(code))) return [];
  return submittedRisks.map((code) => ({ code, detail: ESCALATION_RISKS[code] }));
}
