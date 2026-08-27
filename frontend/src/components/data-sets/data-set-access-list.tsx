import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Separator } from "@/components/ui/separator.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { DataSetRoleOption } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";
import { AddAccessSelector } from "@/components/data-sets/add-access-selector.tsx";
import { AccessRow, AccessSubject } from "@/components/data-sets/access-row.ts";
import { GroupMembersDialog } from "@/components/data-sets/group-members-dialog.tsx";

const api = new ApiClient(authenticationProviderInstance);

export interface DataSetAccessListProps {
  dataSetId: number;
}

export function DataSetAccessList({ dataSetId }: DataSetAccessListProps) {
  const [rows, setRows] = useState<AccessRow[]>([]);
  const [subjects, setSubjects] = useState<AccessSubject[]>([]);
  const [roles, setRoles] = useState<DataSetRoleOption[]>([]);
  const [isAccessDenied, setIsAccessDenied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inspectedGroup, setInspectedGroup] = useState<AccessSubject | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const access = await api.dataSets().getDataSetAccess(dataSetId);
      setRows([
        ...access.users.map((assignment) => ({
          subject: { type: "user" as const, id: assignment.user.id, label: assignment.user.email },
          role: assignment.role
        })),
        ...access.groups.map((assignment) => ({
          subject: {
            type: "group" as const,
            id: assignment.group.id,
            label: assignment.group.name,
            memberCount: assignment.group.memberCount
          },
          role: assignment.role
        }))
      ]);
      setIsAccessDenied(false);
    } catch (loadError) {
      const isDenial = loadError instanceof ApiError
        && (loadError.response.status === 403 || loadError.response.status === 404);
      if (isDenial) {
        setIsAccessDenied(true);
      } else {
        setError("Could not load this data set's access.");
      }
      return;
    }

    try {
      const [users, serviceAccounts, groups, dataSetRoles] = await Promise.all([
        api.getAllUsers(),
        api.serviceAccounts().getAllServiceAccounts(),
        api.groups().getGroups(),
        api.dataSetRoles().getDataSetRoles(),
      ]);
      setSubjects([
        ...users.map((user) => ({ type: "user" as const, id: user.id, label: user.email })),
        ...serviceAccounts.map((serviceAccount) => ({
          type: "user" as const,
          id: serviceAccount.id,
          label: `${serviceAccount.email} (service account)`
        })),
        ...groups.map((group) => ({
          type: "group" as const, id: group.id, label: group.name, memberCount: group.memberCount
        })),
      ]);
      setRoles(dataSetRoles);
    } catch {
      setError("Could not load the users, groups and roles to grant.");
    }
  }, [dataSetId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleGrant = async (subject: AccessSubject, roleId: number) => {
    const response = subject.type === "user"
      ? await api.dataSets().grantRoleToUser(dataSetId, roleId, subject.id)
      : await api.dataSets().grantRoleToGroup(dataSetId, roleId, subject.id);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not grant this role.");
      return;
    }
    await load();
  };

  const handleRevoke = async (row: AccessRow) => {
    const response = row.subject.type === "user"
      ? await api.dataSets().revokeRoleFromUser(dataSetId, row.role.id, row.subject.id)
      : await api.dataSets().revokeRoleFromGroup(dataSetId, row.role.id, row.subject.id);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not revoke this role.");
      return;
    }
    await load();
  };

  if (isAccessDenied) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-medium text-gray-500">
          You don't have permission to manage this data set's access.
        </p>
      </div>
    );
  }

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      <AddAccessSelector subjects={subjects} roles={roles} grantedRoles={rows} onSubmit={handleGrant} />
      <Separator className="my-6" />
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nobody holds a role on this data set yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={`${row.subject.type}-${row.subject.id}-${row.role.id}`}>
                <TableCell width="15%">{row.subject.type === "user" ? "User" : "Group"}</TableCell>
                <TableCell width="45%">
                  {row.subject.label}
                  {row.subject.type === "group" && (
                    <Button
                      variant="link"
                      className="h-auto p-0 ml-2 text-muted-foreground"
                      onClick={() => setInspectedGroup(row.subject)}
                    >
                      {row.subject.memberCount} {row.subject.memberCount === 1 ? "member" : "members"}
                    </Button>
                  )}
                </TableCell>
                <TableCell width="20%">{row.role.name}</TableCell>
                <TableCell className="flex space-x-4" width="20%">
                  <Button onClick={() => handleRevoke(row)} variant="secondary">Remove</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <GroupMembersDialog
        groupId={inspectedGroup?.id ?? null}
        groupName={inspectedGroup?.label ?? ""}
        onClose={() => setInspectedGroup(null)}
      />
    </>
  );
}
