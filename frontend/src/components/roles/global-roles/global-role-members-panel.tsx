import { useCallback } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { AssignmentOption, groupOption, subjectOption } from "@/components/roles/assignment/assignment-option.ts";
import { AssignmentPanel } from "@/components/roles/assignment/assignment-panel.tsx";
import { useAssignments } from "@/components/roles/assignment/use-assignments.ts";
import {
  SUBJECT_PICKER_NOTICE,
  useSubjectCandidates,
  withoutGranted
} from "@/components/roles/assignment/use-subject-candidates.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GlobalRoleMembersPanelProps {
  globalRoleId: number;
}

export function GlobalRoleMembersPanel({ globalRoleId }: GlobalRoleMembersPanelProps) {
  const { hasPermission } = useApplicationContext()!;
  const canAssign = hasPermission(PERMISSIONS.GLOBAL_ROLE.ASSIGN);
  const loadSubjects = useSubjectCandidates();

  const loadItems = useCallback(async () => {
    const [members, groups] = await Promise.all([
      api.globalRoles().getGlobalRoleMembers(globalRoleId),
      api.globalRoles().getGlobalRoleGroups(globalRoleId),
    ]);
    return [...members.map(subjectOption), ...groups.map(groupOption)];
  }, [globalRoleId]);

  const loadCandidates = useCallback(
    async (granted: AssignmentOption[]) => withoutGranted(await loadSubjects(), granted),
    [loadSubjects]
  );

  const { items, candidates, error, pickerNotice, submit } = useAssignments({
    canAssign,
    loadItems,
    loadCandidates,
    itemsError: "Could not load who holds this global role.",
    candidatesNotice: SUBJECT_PICKER_NOTICE,
  });

  return (
    <AssignmentPanel
      items={items}
      candidates={candidates}
      canAssign={canAssign}
      columnLabel="Name"
      emptyMessage="Nobody holds this global role yet."
      pickerPlaceholder="Select a member..."
      error={error}
      pickerNotice={pickerNotice}
      onAdd={(option) => submit(
        option.kind === "group"
          ? api.globalRoles().addGlobalRoleGroup(globalRoleId, option.id)
          : api.globalRoles().addGlobalRoleMember(globalRoleId, option.id),
        "Could not add this member."
      )}
      onRemove={(option) => submit(
        option.kind === "group"
          ? api.globalRoles().removeGlobalRoleGroup(globalRoleId, option.id)
          : api.globalRoles().removeGlobalRoleMember(globalRoleId, option.id),
        "Could not remove this member."
      )}
    />
  );
}
