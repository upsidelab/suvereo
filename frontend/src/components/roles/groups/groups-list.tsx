import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GroupMember, GroupOption } from "@/lib/types.ts";
import { GroupModal } from "@/components/roles/groups/group-modal.tsx";

const api = new ApiClient(authenticationProviderInstance);
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
                <GroupModal group={group} onSaved={load} />
                {group.name !== ADMIN_GROUP_NAME &&
                  <Button variant="secondary" onClick={() => handleDeleteClick(group)}>Delete</Button>
                }
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete group{groupToDelete ? ` "${groupToDelete.name}"` : ""}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              {memberCountToDelete > 0
                ? `This will revoke access for ${memberCountToDelete} member${memberCountToDelete === 1 ? "" : "s"}. This action cannot be undone.`
                : "This action cannot be undone."}
            </p>
          </div>
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={cancelDelete}>Cancel</Button>
            <Button variant="destructive" onClick={confirmDelete}>Delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
