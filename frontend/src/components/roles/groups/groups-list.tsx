import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GroupOption } from "@/lib/types.ts";
import { NewGroupModal } from "@/components/roles/groups/new-group-modal.tsx";
import { GroupMembersModal } from "@/components/roles/groups/group-members-modal.tsx";

const api = new ApiClient(authenticationProviderInstance);
const ADMIN_GROUP_NAME = "Admin";

export function GroupsList() {
  const [groups, setGroups] = useState<GroupOption[]>([]);

  const load = useCallback(async () => {
    setGroups(await api.groups().getGroups());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (group: GroupOption) => {
    await api.groups().deleteGroup(group.id);
    await load();
  };

  return (
    <>
      <div className="flex flex-col items-end mb-4">
        <NewGroupModal onGroupCreated={load} />
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
