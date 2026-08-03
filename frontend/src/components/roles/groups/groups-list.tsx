import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { GroupMember, GroupOption } from "@/lib/types.ts";
import { GroupModal } from "@/components/roles/groups/group-modal.tsx";
import { RevokeConfirmDialog } from "@/components/roles/revoke-confirm-dialog.tsx";

const api = new ApiClient();
const ADMIN_GROUP_NAME = "Admin";

export function GroupsList() {
  const [groups, setGroups] = useState<GroupOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [groupToDelete, setGroupToDelete] = useState<GroupOption | null>(null);
  const [memberCountToDelete, setMemberCountToDelete] = useState(0);

  const load = useCallback(async () => {
    setGroups(await api.groups().getGroups());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDeleteClick = async (group: GroupOption) => {
    setError(null);
    let members: GroupMember[];
    try {
      members = await api.groups().getGroupMembers(group.id);
    } catch {
      setError("Could not load this group's members.");
      return;
    }
    setGroupToDelete(group);
    setMemberCountToDelete(members.length);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!groupToDelete) return;
    const response = await api.groups().deleteGroup(groupToDelete.id);
    setIsDeleteDialogOpen(false);
    setGroupToDelete(null);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? "Could not delete this group.");
      return;
    }
    await load();
  };

  const cancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setGroupToDelete(null);
  };

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      <div className="flex flex-col items-end mb-4">
        <GroupModal onSaved={load} />
      </div>
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="w-48">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groups.map((group) => (
            <TableRow key={group.id}>
              <TableCell>{group.name}</TableCell>
              <TableCell className="flex space-x-4">
                <GroupModal group={group} onSaved={load} />
                {group.name !== ADMIN_GROUP_NAME &&
                  <Button variant="secondary" onClick={() => handleDeleteClick(group)}>Delete</Button>
                }
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <RevokeConfirmDialog
        open={isDeleteDialogOpen}
        title={`Delete group${groupToDelete ? ` "${groupToDelete.name}"` : ""}`}
        count={memberCountToDelete}
        unitLabel="member"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </>
  );
}
