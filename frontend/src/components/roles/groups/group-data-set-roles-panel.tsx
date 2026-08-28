import { useCallback } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { AssignmentOption, roleOption } from "@/components/roles/assignment/assignment-option.ts";
import { AssignmentPanel } from "@/components/roles/assignment/assignment-panel.tsx";
import { DataSetSelect } from "@/components/roles/assignment/data-set-select.tsx";
import { GroupReachNote } from "@/components/roles/assignment/group-reach-note.tsx";
import { useAssignments } from "@/components/roles/assignment/use-assignments.ts";
import { useDataSetScope } from "@/components/roles/assignment/use-data-set-scope.ts";
import { withoutGranted } from "@/components/roles/assignment/use-subject-candidates.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GroupDataSetRolesPanelProps {
  groupId: number;
  memberCount: number;
  onChanged?: () => void;
}

export function GroupDataSetRolesPanel({ groupId, memberCount, onChanged }: GroupDataSetRolesPanelProps) {
  const { hasPermission } = useApplicationContext()!;
  const canAssign = hasPermission(PERMISSIONS.DATA_SET_ROLE.ASSIGN);
  const scope = useDataSetScope(canAssign);
  const { dataSetId } = scope;

  const loadItems = useCallback(async () => {
    const access = await api.dataSets().getDataSetAccess(dataSetId!);
    return access.groups
      .filter((assignment) => assignment.group.id === groupId)
      .map((assignment) => roleOption(assignment.role));
  }, [dataSetId, groupId]);

  const loadCandidates = useCallback(
    async (granted: AssignmentOption[]) =>
      withoutGranted((await api.dataSetRoles().getDataSetRoles()).map(roleOption), granted),
    []
  );

  const { items, candidates, error, pickerNotice, submit } = useAssignments({
    canAssign,
    loadItems: scope.isReady ? loadItems : null,
    loadCandidates,
    itemsError: "Could not load the roles this group holds on that data set.",
    candidatesNotice: "You need the Data Set Role → View permission to grant roles by name.",
    onChanged,
  });

  return (
    <AssignmentPanel
      items={items}
      candidates={candidates}
      canAssign={scope.isReady}
      columnLabel="Data set role"
      emptyMessage={scope.message({
        needsAssign: "You can't see what this group holds on a data set. "
          + "It needs the Data Set Role → Assign permission.",
        noDataSets: "You have no data sets to grant a role on.",
        unselected: "Select a data set to see what this group holds on it.",
        empty: "This group holds no roles on that data set.",
      })}
      pickerPlaceholder="Select a data set role..."
      addLabel="Grant"
      removeLabel="Revoke"
      error={error}
      pickerNotice={pickerNotice}
      onAdd={(option) => submit(
        api.dataSets().grantRoleToGroup(dataSetId!, option.id, groupId), "Could not grant this role.")}
      onRemove={(option) => submit(
        api.dataSets().revokeRoleFromGroup(dataSetId!, option.id, groupId), "Could not revoke this role.")}
    >
      {scope.showSelector && (
        <DataSetSelect dataSets={scope.dataSets} selectedDataSetId={dataSetId} onChange={scope.setDataSetId} />
      )}
      <GroupReachNote memberCount={memberCount} />
    </AssignmentPanel>
  );
}
