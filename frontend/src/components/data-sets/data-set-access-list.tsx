import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { useCallback, useEffect, useState } from "react";
import { AddAccessSelector } from "@/components/data-sets/add-access-selector.tsx";
import { Separator } from "@/components/ui/separator.tsx";
import { DataSetAccessGrant, DatasetRoleOption, GroupOption, User } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

const api = new ApiClient();

export interface DataSetAccessListProps {
  dataSetId: number;
}

export function DataSetAccessList({dataSetId}: DataSetAccessListProps) {
  const [grants, setGrants] = useState<DataSetAccessGrant[]>([]);
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  const [availableGroups, setAvailableGroups] = useState<GroupOption[]>([]);
  const [availableRoles, setAvailableRoles] = useState<DatasetRoleOption[]>([]);
  const [usersLoadFailed, setUsersLoadFailed] = useState(false);
  const [groupsLoadFailed, setGroupsLoadFailed] = useState(false);
  const [rolesLoadFailed, setRolesLoadFailed] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);

  const load = useCallback(async () => {
    let grants: DataSetAccessGrant[];
    try {
      grants = await api.dataSets().getDataSetAccess(dataSetId);
      setAccessDenied(false);
    } catch (err) {
      if (err instanceof ApiError && err.response.status === 403) {
        setAccessDenied(true);
        return;
      }
      throw err;
    }
    setGrants(grants);

    const assignedUserIds = new Set(grants.filter((g) => g.targetType === "user").map((g) => g.targetId));
    const assignedGroupIds = new Set(grants.filter((g) => g.targetType === "group").map((g) => g.targetId));

    try {
      const [systemUsers, serviceAccounts] = await Promise.all([
        api.getAllUsers(),
        api.serviceAccounts().getAllServiceAccounts(),
      ]);
      const allTargets: User[] = [
        ...systemUsers,
        ...serviceAccounts.map((sa) => ({
          id: sa.id,
          email: `${sa.email} (service account)`,
          isActive: sa.isActive,
          isAdmin: sa.isAdmin,
          groupIds: sa.groupIds,
        })),
      ];
      setAvailableUsers(allTargets.filter((u) => !assignedUserIds.has(u.id)));
      setUsersLoadFailed(false);
    } catch {
      setAvailableUsers([]);
      setUsersLoadFailed(true);
    }

    try {
      const systemGroups = await api.groups().getGroups();
      setAvailableGroups(systemGroups.filter((g) => !assignedGroupIds.has(g.id)));
      setGroupsLoadFailed(false);
    } catch {
      setAvailableGroups([]);
      setGroupsLoadFailed(true);
    }

    try {
      const roles = await api.datasetRoles().getDatasetRoles();
      setAvailableRoles(roles);
      setRolesLoadFailed(false);
    } catch {
      setAvailableRoles([]);
      setRolesLoadFailed(true);
    }
  }, [dataSetId]);

  useEffect(() => {
    load();
  }, [load, dataSetId]);

  const handleAdd = async (targetType: "user" | "group", targetId: number, role: string) => {
    await api.dataSets().grantDataSetAccess(dataSetId, targetType, targetId, role);
    await load();
  }

  const handleRemove = async (grant: DataSetAccessGrant) => {
    await api.dataSets().revokeDataSetAccess(dataSetId, grant.targetType, grant.targetId);
    await load();
  }

  if (accessDenied) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-medium text-gray-500">You don't have permission to manage this data set's access.</p>
      </div>
    );
  }

  return (
    <>
      {usersLoadFailed &&
        <p className="text-sm text-muted-foreground mb-4">
          Unable to load users — you may need account.manage_users to add individual users; group access still works.
        </p>
      }
      {groupsLoadFailed &&
        <p className="text-sm text-muted-foreground mb-4">
          Unable to load groups — group access still works for groups already granted access.
        </p>
      }
      {rolesLoadFailed &&
        <p className="text-sm text-muted-foreground mb-4">
          Unable to load dataset roles — you may need Admin-group membership.
        </p>
      }
      <AddAccessSelector
        availableUsers={availableUsers}
        availableGroups={availableGroups}
        availableRoles={availableRoles}
        onSubmit={handleAdd}
      />
      <Separator className="my-6"/>
      {grants.length > 0 &&
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
            {grants.map((grant, index) => (
              <TableRow key={index}>
                <TableCell width="15%">
                  {grant.targetType === "user" ? "User" : "Group"}
                </TableCell>
                <TableCell width="45%">
                  {grant.targetLabel}
                </TableCell>
                <TableCell width="20%">
                  {grant.role ?? "Custom"}
                </TableCell>
                <TableCell className="flex space-x-4" width="20%">
                  <Button onClick={() => {
                    handleRemove(grant)
                  }} variant="secondary">Remove</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      }
    </>
  );
}
