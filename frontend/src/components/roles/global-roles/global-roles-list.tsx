import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GroupOption } from "@/lib/types.ts";
import { GlobalRoleModal } from "@/components/roles/global-roles/global-role-modal.tsx";
import { GroupMembersModal } from "@/components/roles/groups/group-members-modal.tsx";

const api = new ApiClient(authenticationProviderInstance);
const ADMIN_GROUP_NAME = "Admin";

export function GlobalRolesList() {
  const [groups, setGroups] = useState<GroupOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setGroups(await api.groups().getGroups());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (group: GroupOption) => {
    setError(null);
    const response = await api.groups().deleteGroup(group.id);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? "Could not delete this role.");
      return;
    }
    await load();
  };

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      <div className="flex flex-col items-end mb-4">
        <GlobalRoleModal onSaved={load} />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groups.map((group) => (
            <TableRow key={group.id}>
              <TableCell>{group.name}</TableCell>
              <TableCell className="flex space-x-4">
                <GlobalRoleModal group={group} onSaved={load} />
                <GroupMembersModal groupId={group.id} groupName={group.name} />
                {group.name !== ADMIN_GROUP_NAME &&
                  <Button variant="secondary" onClick={() => handleDelete(group)}>Delete</Button>
                }
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}
