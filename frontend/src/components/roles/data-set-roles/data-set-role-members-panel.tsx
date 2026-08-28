import { useCallback } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { AssignmentOption, groupOption, subjectOption } from "@/components/roles/assignment/assignment-option.ts";
import { AssignmentPanel } from "@/components/roles/assignment/assignment-panel.tsx";
import { DataSetSelect } from "@/components/roles/assignment/data-set-select.tsx";
import { useAssignments } from "@/components/roles/assignment/use-assignments.ts";
import { useDataSetScope } from "@/components/roles/assignment/use-data-set-scope.ts";
import {
  SUBJECT_PICKER_NOTICE,
  useSubjectCandidates,
  withoutGranted
} from "@/components/roles/assignment/use-subject-candidates.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface DataSetRoleMembersPanelProps {
  roleId: number;
}

/** One data set at a time - the grant is per data set. */
export function DataSetRoleMembersPanel({ roleId }: DataSetRoleMembersPanelProps) {
  const { hasPermission } = useApplicationContext()!;
  const canAssign = hasPermission(PERMISSIONS.DATA_SET_ROLE.ASSIGN);
  const scope = useDataSetScope(canAssign);
  const loadSubjects = useSubjectCandidates();
  const { dataSetId } = scope;

  const loadItems = useCallback(async () => {
    const access = await api.dataSets().getDataSetAccess(dataSetId!);
    const forThisRole = <T extends { role: { id: number } }>(assignment: T) => assignment.role.id === roleId;
    return [
      ...access.members.filter(forThisRole).map((assignment) => subjectOption(assignment.user)),
      ...access.groups.filter(forThisRole).map((assignment) => groupOption(assignment.group)),
    ];
  }, [dataSetId, roleId]);

  const loadCandidates = useCallback(
    async (granted: AssignmentOption[]) => withoutGranted(await loadSubjects(), granted),
    [loadSubjects]
  );

  const { items, candidates, error, pickerNotice, submit } = useAssignments({
    canAssign,
    loadItems: scope.isReady ? loadItems : null,
    loadCandidates,
    itemsError: "Could not load who holds this role on that data set.",
    candidatesNotice: SUBJECT_PICKER_NOTICE,
  });

  return (
    <AssignmentPanel
      items={items}
      candidates={candidates}
      canAssign={scope.isReady}
      columnLabel="Name"
      emptyMessage={scope.message({
        needsAssign: "You can't see who holds this role. It needs the Data Set Role → Assign permission.",
        noDataSets: "You have no data sets to grant this role on.",
        unselected: "Select a data set to see who holds this role on it.",
        empty: "Nobody holds this role on that data set yet.",
      })}
      pickerPlaceholder="Select a member..."
      addLabel="Grant"
      removeLabel="Revoke"
      error={error}
      pickerNotice={pickerNotice}
      onAdd={(option) => submit(
        option.kind === "group"
          ? api.dataSets().grantRoleToGroup(dataSetId!, roleId, option.id)
          : api.dataSets().grantRoleToMember(dataSetId!, roleId, option.id),
        "Could not grant this role."
      )}
      onRemove={(option) => submit(
        option.kind === "group"
          ? api.dataSets().revokeRoleFromGroup(dataSetId!, roleId, option.id)
          : api.dataSets().revokeRoleFromMember(dataSetId!, roleId, option.id),
        "Could not revoke this role."
      )}
    >
      {scope.showSelector && (
        <DataSetSelect dataSets={scope.dataSets} selectedDataSetId={dataSetId} onChange={scope.setDataSetId} />
      )}
    </AssignmentPanel>
  );
}
