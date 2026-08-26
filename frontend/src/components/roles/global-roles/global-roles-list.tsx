import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { GlobalRoleModal } from "@/components/roles/global-roles/global-role-modal.tsx";
import { RevokeConfirmDialog } from "@/components/roles/revoke-confirm-dialog.tsx";
import { ADMIN_ROLE, GlobalRole } from "@/components/roles/global-roles/admin-role.ts";
import { ApiError } from "@/lib/api-error.ts";
import { PERMISSIONS } from "@/lib/permissions.ts";

const api = new ApiClient(authenticationProviderInstance);

export function GlobalRolesList() {
  const { hasPermission } = useApplicationContext()!;
  const canAddRoles = hasPermission(PERMISSIONS.GLOBAL_ROLE.ADD);
  const canDeleteRoles = hasPermission(PERMISSIONS.GLOBAL_ROLE.DELETE);
  const [groups, setGroups] = useState<GlobalRole[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAccessDenied, setIsAccessDenied] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [groupToDelete, setGroupToDelete] = useState<GlobalRole | null>(null);

  const load = useCallback(async () => {
    try {
      setGroups(await api.globalRoles().getGlobalRoles());
      setIsAccessDenied(false);
      setError(null);
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.response.status === 403) {
        setIsAccessDenied(true);
        return;
      }
      setError("Failed to load the list of roles.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const confirmDelete = async () => {
    if (groupToDelete?.id == null) return;
    const response = await api.globalRoles().deleteGlobalRole(groupToDelete.id);
    setIsDeleteDialogOpen(false);
    setGroupToDelete(null);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not delete this role.");
      return;
    }
    await load();
  };

  const cancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setGroupToDelete(null);
  };

  const rows: GlobalRole[] = [ADMIN_ROLE, ...groups];

  if (isLoading) {
    return null;
  }

  if (isAccessDenied) {
    return <p className="text-sm text-destructive">You don't have access to the list of roles.</p>;
  }

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {canAddRoles && (
        <div className="flex flex-col items-end mb-4">
          <GlobalRoleModal onSaved={load} />
        </div>
      )}
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className={canDeleteRoles ? "w-48" : "w-24"}>Action</TableHead>
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
                <GlobalRoleModal role={role} onSaved={load} />
                {canDeleteRoles && !role.isBuiltIn && (
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
        description="Its members lose everything it granted them, on every data set where it held a role. This action cannot be undone."
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </>
  );
}
