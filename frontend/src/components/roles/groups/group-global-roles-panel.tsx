import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button.tsx";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GlobalRoleOption } from "@/lib/types.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GroupGlobalRolesPanelProps {
  groupId: number;
  memberCount: number;
  onChanged?: () => void;
}

export function GroupGlobalRolesPanel({ groupId, memberCount, onChanged }: GroupGlobalRolesPanelProps) {
  const { hasPermission } = useApplicationContext()!;
  const canAssign = hasPermission(PERMISSIONS.GLOBAL_ROLE.ASSIGN);
  const [held, setHeld] = useState<GlobalRoleOption[]>([]);
  const [candidates, setCandidates] = useState<GlobalRoleOption[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [pickerError, setPickerError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    let current: GlobalRoleOption[];
    try {
      current = (await api.groups().getGroupDetail(groupId)).globalRoles;
    } catch {
      setError("Could not load the roles this group holds.");
      return;
    }
    setHeld(current);

    if (!canAssign) return;

    try {
      const heldIds = new Set(current.map((globalRole) => globalRole.id));
      const globalRoles = await api.globalRoles().getGlobalRoles();
      setCandidates(globalRoles.filter((globalRole) => !heldIds.has(globalRole.id)));
      setPickerError(null);
    } catch {
      setCandidates([]);
      setPickerError("You need the Global Role → View permission to grant roles by name.");
    }
  }, [groupId, canAssign]);

  useEffect(() => {
    load();
  }, [load]);

  const handleGrant = async () => {
    if (!selectedRoleId) return;
    const response = await api.groups().grantGlobalRoleToGroup(groupId, Number(selectedRoleId));
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not grant this role.");
      return;
    }
    setSelectedRoleId("");
    await load();
    onChanged?.();
  };

  const handleRevoke = async (globalRole: GlobalRoleOption) => {
    const response = await api.groups().revokeGlobalRoleFromGroup(groupId, globalRole.id);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not revoke this role.");
      return;
    }
    await load();
    onChanged?.();
  };

  return (
    <div className="flex flex-col grow min-h-0">
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {/* Granting hands the role to everyone already inside the group, so the size of the bucket
          belongs next to the control that hands it out. */}
      <p className="text-sm text-muted-foreground mb-4">
        Everything granted here reaches{" "}
        {memberCount === 1 ? "the 1 member" : `all ${memberCount} members`} of this group,
        and anyone added to it later.
      </p>
      {canAssign && (
        pickerError
          ? <p className="text-sm text-muted-foreground mb-4">{pickerError}</p>
          : (
            <div className="flex space-x-4 mb-4">
              <Select value={selectedRoleId} onValueChange={setSelectedRoleId}>
                <SelectTrigger className="w-[300px]">
                  <SelectValue placeholder="Select a global role..." />
                </SelectTrigger>
                <SelectContent>
                  {candidates.map((globalRole) => (
                    <SelectItem key={globalRole.id} value={String(globalRole.id)}>{globalRole.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={handleGrant} disabled={!selectedRoleId}>Grant</Button>
            </div>
          )
      )}
      <ScrollArea className="grow min-h-0 w-full rounded-md border px-4 py-2">
        {held.length === 0 ? (
          <p className="text-sm text-muted-foreground">This group holds no global roles.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-full">Global role</TableHead>
                {canAssign && <TableHead className="whitespace-nowrap">Action</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {held.map((globalRole) => (
                <TableRow key={globalRole.id}>
                  <TableCell width="100%">{globalRole.name}</TableCell>
                  {canAssign && (
                    <TableCell className="whitespace-nowrap">
                      <Button variant="secondary" onClick={() => handleRevoke(globalRole)}>Revoke</Button>
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
