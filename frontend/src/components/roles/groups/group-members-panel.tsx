import { useCallback } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { AssignmentOption, subjectOption } from "@/components/roles/assignment/assignment-option.ts";
import { AssignmentPanel } from "@/components/roles/assignment/assignment-panel.tsx";
import { useAssignments } from "@/components/roles/assignment/use-assignments.ts";
import { withoutGranted } from "@/components/roles/assignment/use-subject-candidates.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GroupMembersPanelProps {
  groupId: number;
  onChanged?: () => void;
}

export function GroupMembersPanel({ groupId, onChanged }: GroupMembersPanelProps) {
  const { hasPermission } = useApplicationContext()!;
  const canAssign = hasPermission(PERMISSIONS.GROUP.ASSIGN);

  const loadItems = useCallback(
    async () => (await api.groups().getGroupMembers(groupId)).map(subjectOption),
    [groupId]
  );

  // No group nesting, so this cannot use the shared subject loader.
  const loadCandidates = useCallback(async (granted: AssignmentOption[]) => {
    const [users, serviceAccounts] = await Promise.all([
      api.getAllUsers(),
      api.serviceAccounts().getAllServiceAccounts(),
    ]);
    return withoutGranted([
      ...users.map((user) => subjectOption({ ...user, isServiceAccount: false })),
      ...serviceAccounts.map((account) => subjectOption({ ...account, isServiceAccount: true })),
    ], granted);
  }, []);

  const { items, candidates, error, pickerNotice, submit } = useAssignments({
    canAssign,
    loadItems,
    loadCandidates,
    itemsError: "Could not load this group's members.",
    candidatesNotice: "You need the User → View permission to add members by name.",
    onChanged,
  });

  return (
    <AssignmentPanel
      items={items}
      candidates={candidates}
      canAssign={canAssign}
      columnLabel="Name"
      emptyMessage="No members yet."
      pickerPlaceholder="Select a member..."
      error={error}
      pickerNotice={pickerNotice}
      onAdd={(option) =>
        submit(api.groups().addGroupMember(groupId, option.id), "Could not add this member.")}
      onRemove={(option) =>
        submit(api.groups().removeGroupMember(groupId, option.id), "Could not remove this member.")}
    />
  );
}
