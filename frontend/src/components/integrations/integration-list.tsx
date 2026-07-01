import { useCallback, useEffect, useState } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { Integration } from "@/lib/types.ts";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { ButtonWithTooltip } from "@/components/ui/button-with-tooltip.tsx";
import { AddIntegrationModal } from "@/components/integrations/add-integration-modal.tsx";

const api = new ApiClient(authenticationProviderInstance);

interface IntegrationListProps {
  dataSetId: number;
}

export function IntegrationList({ dataSetId }: IntegrationListProps) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [integrationToDelete, setIntegrationToDelete] = useState<Integration | null>(null);

  const loadIntegrations = useCallback(async () => {
    const result = await api.integrations().list(dataSetId);
    setIntegrations(result);
  }, [dataSetId]);

  useEffect(() => {
    loadIntegrations();
  }, [loadIntegrations]);

  const handleSync = async (integration: Integration) => {
    await api.integrations().sync(dataSetId, integration.id);
  };

  const handleDeleteClick = (integration: Integration) => {
    setIntegrationToDelete(integration);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!integrationToDelete) return;
    await api.integrations().delete(dataSetId, integrationToDelete.id);
    await loadIntegrations();
    setIsDeleteDialogOpen(false);
    setIntegrationToDelete(null);
  };

  const cancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setIntegrationToDelete(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button onClick={() => setIsAddModalOpen(true)}>
          <Plus className="h-4 w-4" />
          Add integration
        </Button>
      </div>

      {integrations.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Added</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {integrations.map(integration => (
              <TableRow key={integration.id}>
                <TableCell className="font-medium">{integration.type}</TableCell>
                <TableCell>{new Date(integration.created_at).toLocaleDateString()}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end space-x-2">
                    <ButtonWithTooltip
                      variant="outline"
                      size="sm"
                      onClick={() => handleSync(integration)}
                      tooltip="Synchronize data"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </ButtonWithTooltip>
                    <ButtonWithTooltip
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteClick(integration)}
                      tooltip="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </ButtonWithTooltip>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <div className="text-center py-12">
          <div className="text-gray-500 mb-6">
            <p className="text-lg font-medium">No integrations configured</p>
            <p className="text-sm">Add an integration to start importing data</p>
          </div>
          <Button onClick={() => setIsAddModalOpen(true)}>
            <Plus className="h-4 w-4" />
            Add integration
          </Button>
        </div>
      )}

      <AddIntegrationModal
        dataSetId={dataSetId}
        open={isAddModalOpen}
        onOpenChange={setIsAddModalOpen}
        onSuccess={loadIntegrations}
      />

      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Integration</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Are you sure you want to delete this integration? This action cannot be undone.
              Data already imported will be kept.
            </p>
          </div>
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={cancelDelete}>Cancel</Button>
            <Button variant="destructive" onClick={confirmDelete}>Delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
