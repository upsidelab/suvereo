import { useCallback } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { AssignmentOption, roleOption } from "@/components/roles/assignment/assignment-option.ts";
import { AssignmentPanel } from "@/components/roles/assignment/assignment-panel.tsx";
import { GroupReachNote } from "@/components/roles/assignment/group-reach-note.tsx";
import { useAssignments } from "@/components/roles/assignment/use-assignments.ts";
import { withoutGranted } from "@/components/roles/assignment/use-subject-candidates.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GroupGlobalRolesPanelProps {
  groupId: number;
  memberCount: number;
  onChanged?: () => void;
}

export function GroupGlobalRolesPanel({ groupId, memberCount, onChanged }: GroupGlobalRolesPanelProps) {
  const { hasPermission } = useApplicationContext()!;
  const canAssign = hasPermission(PERMISSIONS.GLOBAL_ROLE.ASSIGN);

  const loadItems = useCallback(
    async () => (await api.groups().getGroupDetail(groupId)).globalRoles.map(roleOption),
    [groupId]
  );

  const loadCandidates = useCallback(
    async (granted: AssignmentOption[]) =>
      withoutGranted((await api.globalRoles().getGlobalRoles()).map(roleOption), granted),
    []
  );

  const { items, candidates, error, pickerNotice, submit } = useAssignments({
    canAssign,
    loadItems,
    loadCandidates,
    itemsError: "Could not load the global roles this group holds.",
    candidatesNotice: "You need the Global Role → View permission to grant roles by name.",
    onChanged,
  });

  return (
    <AssignmentPanel
      items={items}
      candidates={candidates}
      canAssign={canAssign}
      columnLabel="Global role"
      emptyMessage="This group holds no global roles."
      pickerPlaceholder="Select a global role..."
      pickerEmptyPlaceholder="No global roles left to grant"
      addLabel="Grant"
      removeLabel="Revoke"
      error={error}
      pickerNotice={pickerNotice}
      onAdd={(option) => submit(
        api.groups().grantGlobalRoleToGroup(groupId, option.id), "Could not grant this global role.")}
      onRemove={(option) => submit(
        api.groups().revokeGlobalRoleFromGroup(groupId, option.id), "Could not revoke this global role.")}
    >
      <GroupReachNote memberCount={memberCount} />
    </AssignmentPanel>
  );
}
