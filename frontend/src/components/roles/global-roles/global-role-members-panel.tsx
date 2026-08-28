import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button.tsx";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GlobalRoleMember } from "@/lib/types.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GlobalRoleMembersPanelProps {
  globalRoleId: number;
}

export function GlobalRoleMembersPanel({ globalRoleId }: GlobalRoleMembersPanelProps) {
  const { hasPermission } = useApplicationContext()!;
  const canAssign = hasPermission(PERMISSIONS.GLOBAL_ROLE.ASSIGN);
  const [members, setMembers] = useState<GlobalRoleMember[]>([]);
  const [candidates, setCandidates] = useState<GlobalRoleMember[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [pickerError, setPickerError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    let currentMembers: GlobalRoleMember[];
    try {
      currentMembers = await api.globalRoles().getGlobalRoleMembers(globalRoleId);
    } catch {
      setError("Could not load this global role's members.");
      return;
    }
    setMembers(currentMembers);

    if (!canAssign) return;

    try {
      const [users, serviceAccounts] = await Promise.all([
        api.getAllUsers(),
        api.serviceAccounts().getAllServiceAccounts(),
      ]);
      const memberIds = new Set(currentMembers.map((member) => member.id));
      setCandidates([
        ...users.map((user) => ({ id: user.id, email: user.email, isServiceAccount: false })),
        ...serviceAccounts.map((account) => ({ id: account.id, email: account.email, isServiceAccount: true })),
      ].filter((candidate) => !memberIds.has(candidate.id)));
      setPickerError(null);
    } catch {
      setCandidates([]);
      setPickerError("You need the User → View permission to add members by name.");
    }
  }, [globalRoleId, canAssign]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    if (!selectedUserId) return;
    const response = await api.globalRoles().addGlobalRoleMember(globalRoleId, Number(selectedUserId));
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not add this member.");
      return;
    }
    setSelectedUserId("");
    await load();
  };

  const handleRemove = async (member: GlobalRoleMember) => {
    const response = await api.globalRoles().removeGlobalRoleMember(globalRoleId, member.id);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not remove this member.");
      return;
    }
    await load();
  };

  return (
    <div className="flex flex-col grow min-h-0">
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {canAssign && (
        pickerError
          ? <p className="text-sm text-muted-foreground mb-4">{pickerError}</p>
          : (
            <div className="flex space-x-4 mb-4">
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger className="w-[300px]">
                  <SelectValue placeholder="Select a user..." />
                </SelectTrigger>
                <SelectContent>
                  {candidates.map((candidate) => (
                    <SelectItem key={`${candidate.isServiceAccount}-${candidate.id}`} value={String(candidate.id)}>
                      {candidate.email}{candidate.isServiceAccount && " (service account)"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={handleAdd} disabled={!selectedUserId}>Add</Button>
            </div>
          )
      )}
      <ScrollArea className="grow min-h-0 w-full rounded-md border px-4 py-2">
        {members.length === 0 ? (
          <p className="text-sm text-muted-foreground">No members yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-full">Email</TableHead>
                {canAssign && <TableHead className="whitespace-nowrap">Action</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((member) => (
                <TableRow key={member.id}>
                  <TableCell width="100%">{member.email}{member.isServiceAccount && " (service account)"}</TableCell>
                  {canAssign && (
                    <TableCell className="whitespace-nowrap">
                      <Button variant="secondary" onClick={() => handleRemove(member)}>Remove</Button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </ScrollArea>
    </div>
  );
}
