import { useCallback, useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { ApiClient } from "@/lib/api.ts";
import { DatasetRoleOption } from "@/lib/types.ts";
import { DatasetRoleModal } from "@/components/roles/dataset-roles/dataset-role-modal.tsx";
import { RevokeConfirmDialog } from "@/components/roles/revoke-confirm-dialog.tsx";

const api = new ApiClient();

export function DatasetRolesList() {
  const [roles, setRoles] = useState<DatasetRoleOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [roleToDelete, setRoleToDelete] = useState<DatasetRoleOption | null>(null);
  const [usageCountToDelete, setUsageCountToDelete] = useState(0);

  const load = useCallback(async () => {
    setRoles(await api.datasetRoles().getDatasetRoles());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDeleteClick = async (role: DatasetRoleOption) => {
    setError(null);
    let usageCount: number;
    try {
      usageCount = await api.datasetRoles().getDatasetRoleUsageCount(role.id);
    } catch {
      setError("Could not check how many grants use this role.");
      return;
    }
    setRoleToDelete(role);
    setUsageCountToDelete(usageCount);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!roleToDelete) return;
    const response = await api.datasetRoles().deleteDatasetRole(roleToDelete.id);
    setIsDeleteDialogOpen(false);
    setRoleToDelete(null);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? "Could not delete this role.");
      return;
    }
    await load();
  };

  const cancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setRoleToDelete(null);
  };

  return (
    <>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      <div className="flex flex-col items-end mb-4">
        <DatasetRoleModal onSaved={load} />
      </div>
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="w-48">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {roles.map((role) => (
            <TableRow key={role.id}>
              <TableCell>{role.name}</TableCell>
              <TableCell className="flex space-x-4">
                <DatasetRoleModal role={role} onSaved={load} />
                <Button variant="secondary" onClick={() => handleDeleteClick(role)}>Delete</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <RevokeConfirmDialog
        open={isDeleteDialogOpen}
        title={`Delete role${roleToDelete ? ` "${roleToDelete.name}"` : ""}`}
        count={usageCountToDelete}
        unitLabel="grant"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </>
  );
}
