import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { DatasetRoleOption } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { DatasetRoleModal } from "@/components/roles/dataset-roles/dataset-role-modal.tsx";
import { RevokeConfirmDialog } from "@/components/roles/revoke-confirm-dialog.tsx";
import { ApiError } from "@/lib/api-error.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";

const api = new ApiClient(authenticationProviderInstance);

export function DatasetRolesList() {
  const { hasPermission } = useApplicationContext()!;
  const canAddRoles = hasPermission(PERMISSIONS.DATASET_ROLE.ADD);
  const canDeleteRoles = hasPermission(PERMISSIONS.DATASET_ROLE.DELETE);
  const [roles, setRoles] = useState<DatasetRoleOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAccessDenied, setIsAccessDenied] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [roleToDelete, setRoleToDelete] = useState<DatasetRoleOption | null>(null);

  const load = useCallback(async () => {
    try {
      setRoles(await api.datasetRoles().getDatasetRoles());
      setIsAccessDenied(false);
      setError(null);
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.response.status === 403) {
        setIsAccessDenied(true);
        return;
      }
      setError("Failed to load the list of dataset roles.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const confirmDelete = async () => {
    if (!roleToDelete) return;
    const response = await api.datasetRoles().deleteDatasetRole(roleToDelete.id);
    setIsDeleteDialogOpen(false);
    setRoleToDelete(null);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not delete this role.");
      return;
    }
    await load();
  };

  const cancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setRoleToDelete(null);
  };

  if (isLoading) {
    return null;
  }

  if (isAccessDenied) {
    return <p className="text-sm text-destructive">You don't have view access to the list of dataset roles.</p>;
  }

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {canAddRoles && (
        <div className="flex flex-col items-end mb-4">
          <DatasetRoleModal onSaved={load} />
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
          {roles.map((role) => (
            <TableRow key={role.id}>
              <TableCell>{role.name}</TableCell>
              <TableCell className="flex space-x-4">
                <DatasetRoleModal role={role} onSaved={load} />
                {canDeleteRoles && (
                  <Button
                    variant="secondary"
                    onClick={() => { setError(null); setRoleToDelete(role); setIsDeleteDialogOpen(true); }}
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
        title={`Delete role${roleToDelete ? ` "${roleToDelete.name}"` : ""}`}
        description="Everyone holding it on any data set loses what it granted. This action cannot be undone."
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </>
  );
}
