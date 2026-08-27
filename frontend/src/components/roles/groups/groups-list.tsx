import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { GroupOption } from "@/lib/types.ts";
import { GroupModal } from "@/components/roles/groups/group-modal.tsx";
import { RevokeConfirmDialog } from "@/components/roles/revoke-confirm-dialog.tsx";
import { ApiError } from "@/lib/api-error.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";

const api = new ApiClient(authenticationProviderInstance);

export function GroupsList() {
  const { hasPermission } = useApplicationContext()!;
  const canAddGroups = hasPermission(PERMISSIONS.GROUP.ADD);
  const canDeleteGroups = hasPermission(PERMISSIONS.GROUP.DELETE);
  const [groups, setGroups] = useState<GroupOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAccessDenied, setIsAccessDenied] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [groupToDelete, setGroupToDelete] = useState<GroupOption | null>(null);

  const load = useCallback(async () => {
    try {
      setGroups(await api.groups().getGroups());
      setIsAccessDenied(false);
      setError(null);
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.response.status === 403) {
        setIsAccessDenied(true);
        return;
      }
      setError("Failed to load the list of groups.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const confirmDelete = async () => {
    if (groupToDelete?.id == null) return;
    const response = await api.groups().deleteGroup(groupToDelete.id);
    setIsDeleteDialogOpen(false);
    setGroupToDelete(null);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not delete this group.");
      return;
    }
    await load();
  };

  const cancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setGroupToDelete(null);
  };

  if (isLoading) {
    return null;
  }

  if (isAccessDenied) {
    return <p className="text-sm text-destructive">You don't have view access to the list of groups.</p>;
  }

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {canAddGroups && (
        <div className="flex flex-col items-end mb-4">
          <GroupModal onSaved={load} />
        </div>
      )}
      {groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">No groups yet.</p>
      ) : (
        <Table className="table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead className="w-32">Members</TableHead>
              <TableHead className="w-48">Roles held</TableHead>
              <TableHead className={canDeleteGroups ? "w-48" : "w-24"}>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groups.map((group) => (
              <TableRow key={group.id}>
                <TableCell>{group.name}</TableCell>
                <TableCell>{group.memberCount}</TableCell>
                <TableCell className="text-muted-foreground">
                  {describeReach(group)}
                </TableCell>
                <TableCell className="flex space-x-4">
                  <GroupModal group={group} onSaved={load} />
                  {canDeleteGroups && (
                    <Button
                      variant="secondary"
                      onClick={() => { setError(null); setGroupToDelete(group); setIsDeleteDialogOpen(true); }}
                    >
                      Delete
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <RevokeConfirmDialog
        open={isDeleteDialogOpen}
        title={`Delete group${groupToDelete ? ` "${groupToDelete.name}"` : ""}`}
        description="Its members lose everything it granted them, on every data set where it held a role. The members themselves and the roles it held are not deleted. This action cannot be undone."
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </>
  );
}

function describeReach(group: GroupOption): string {
  const parts = [
    counted(group.globalRoleCount, "global role"),
    counted(group.datasetRoleCount, "dataset role"),
  ].filter((part) => part !== null);
  return parts.length === 0 ? "None" : parts.join(" · ");
}

function counted(count: number, noun: string): string | null {
  if (count === 0) return null;
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}
