import { useCallback, useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GroupMember, User } from "@/lib/types.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GroupMembersModalProps {
  groupId: number;
  groupName: string;
}

export function GroupMembersModal({ groupId, groupName }: GroupMembersModalProps) {
  const [open, setOpen] = useState(false);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");

  const load = useCallback(async () => {
    const currentMembers = await api.groups().getGroupMembers(groupId);
    setMembers(currentMembers);
    const allUsers = await api.getAllUsers();
    const memberIds = new Set(currentMembers.map((m) => m.id));
    setAvailableUsers(allUsers.filter((u) => !memberIds.has(u.id)));
  }, [groupId]);

  useEffect(() => {
    if (open) {
      load();
    }
  }, [open, load]);

  const handleAdd = async () => {
    if (!selectedUserId) return;
    await api.groups().addGroupMember(groupId, Number(selectedUserId));
    setSelectedUserId("");
    await load();
  };

  const handleRemove = async (userId: number) => {
    await api.groups().removeGroupMember(groupId, userId);
    await load();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="secondary">Members</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Members of {groupName}</DialogTitle>
        </DialogHeader>
        <div className="flex space-x-4 mb-4">
          <Select value={selectedUserId} onValueChange={setSelectedUserId}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Select a user..." />
            </SelectTrigger>
            <SelectContent>
              {availableUsers.map((user) => (
                <SelectItem key={user.id} value={String(user.id)}>{user.email}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleAdd} disabled={!selectedUserId}>Add</Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.map((member) => (
              <TableRow key={member.id}>
                <TableCell>{member.email}</TableCell>
                <TableCell>
                  <Button variant="secondary" onClick={() => handleRemove(member.id)}>Remove</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DialogContent>
    </Dialog>
  );
}
