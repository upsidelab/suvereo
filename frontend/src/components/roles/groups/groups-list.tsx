import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { GroupModal } from "@/components/roles/groups/group-modal.tsx";
import { RevokeConfirmDialog } from "@/components/roles/revoke-confirm-dialog.tsx";
import { ADMIN_ROLE, GlobalRole } from "@/components/roles/groups/admin-role.ts";
import { ApiError } from "@/lib/api-error.ts";

const api = new ApiClient(authenticationProviderInstance);

export function GroupsList() {
  const { account } = useApplicationContext()!;
  const isAdmin = !!account?.isAdmin;
  const [groups, setGroups] = useState<GlobalRole[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isAccessDenied, setIsAccessDenied] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [groupToDelete, setGroupToDelete] = useState<GlobalRole | null>(null);

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
      setError("Failed to load the list of roles.");
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
      const assignments = body.dataset_assignments;
      setError([
        body.detail ?? "Could not delete this role.",
        assignments ? `(${assignments} data set assignment${assignments === 1 ? "" : "s"})` : null,
      ].filter(Boolean).join(" "));
      return;
    }
    await load();
  };

  const cancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setGroupToDelete(null);
  };

  const rows: GlobalRole[] = [ADMIN_ROLE, ...groups];

  if (isAccessDenied) {
    return <p className="text-sm text-destructive">You don't have access to the list of roles.</p>;
  }

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {isAdmin && (
        <div className="flex flex-col items-end mb-4">
          <GroupModal onSaved={load} />
        </div>
      )}
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="w-48">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((role) => (
            <TableRow key={role.id ?? "admin"}>
              <TableCell>
                {role.name}
                {role.isBuiltIn && (
                  <span className="ml-2 rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                    Built-in
                  </span>
                )}
              </TableCell>
              <TableCell className="flex space-x-4">
                <GroupModal role={role} onSaved={load} />
                {isAdmin && !role.isBuiltIn && (
                  <Button
                    variant="secondary"
                    onClick={() => { setError(null); setGroupToDelete(role); setIsDeleteDialogOpen(true); }}
                  >
                    Delete
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <RevokeConfirmDialog
        open={isDeleteDialogOpen}
        title={`Delete role${groupToDelete ? ` "${groupToDelete.name}"` : ""}`}
        description="Its members lose everything it granted them. This action cannot be undone."
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </>
  );
}
