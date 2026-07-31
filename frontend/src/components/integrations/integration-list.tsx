import { useCallback, useEffect, useState } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { ApiError } from "@/lib/api-error.ts";
import { Integration, IntegrationType } from "@/lib/types.ts";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu.tsx";
import { Plus, RefreshCw, Settings, Trash2 } from "lucide-react";
import { ButtonWithTooltip } from "@/components/ui/button-with-tooltip.tsx";
import { AddEditIntegrationModal } from "@/components/integrations/add-edit-integration-modal.tsx";

const api = new ApiClient(authenticationProviderInstance);

function IntegrationTypeBadge({ typeName }: { typeName: string | null }) {
  const colors = typeName ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-500";
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors}`}>
      {typeName ?? "Unknown"}
    </span>
  );
}

interface IntegrationListProps {
  dataSetId: number;
}

export function IntegrationList({ dataSetId }: IntegrationListProps) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [integrationTypes, setIntegrationTypes] = useState<IntegrationType[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTypeName, setModalTypeName] = useState<string | undefined>(undefined);
  const [integrationToEdit, setIntegrationToEdit] = useState<Integration | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [integrationToDelete, setIntegrationToDelete] = useState<Integration | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);

  const loadIntegrations = useCallback(async () => {
    try {
      const result = await api.integrations().list(dataSetId);
      setIntegrations(result);
      setAccessDenied(false);
    } catch (err) {
      if (err instanceof ApiError && err.response.status === 403) {
        setAccessDenied(true);
      } else {
        throw err;
      }
    }
  }, [dataSetId]);

  useEffect(() => {
    loadIntegrations();
    api.integrations().listTypes().then(setIntegrationTypes);
  }, [loadIntegrations]);

  const integrationTypeNames = [...new Set(integrationTypes.map(t => t.integration_type_name))];

  const handleAdd = (typeName: string) => {
    setIntegrationToEdit(null);
    setModalTypeName(typeName);
    setModalOpen(true);
  };

  const handleEdit = (integration: Integration) => {
    setIntegrationToEdit(integration);
    setModalTypeName(undefined);
    setModalOpen(true);
  };

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

  const addIntegrationButton = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button disabled={integrationTypeNames.length === 0}>
          <Plus className="h-4 w-4" />
          Add integration
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {integrationTypeNames.map(typeName => (
          <DropdownMenuItem key={typeName} onClick={() => handleAdd(typeName)}>
            {typeName}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  if (accessDenied) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-medium text-gray-500">
          You don't have permission to view this data set's integrations.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">{addIntegrationButton}</div>

      {integrations.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {integrations.map(integration => (
              <TableRow key={integration.id}>
                <TableCell className="font-medium">{integration.name}</TableCell>
                <TableCell>
                  <IntegrationTypeBadge typeName={integration.integration_type_name} />
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end space-x-2">
                    {integration.configurable && (
                      <ButtonWithTooltip
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(integration)}
                        tooltip="Edit configuration"
                      >
                        <Settings className="h-4 w-4" />
                      </ButtonWithTooltip>
                    )}
                    {integration.syncable && (
                      <ButtonWithTooltip
                        variant="outline"
                        size="sm"
                        onClick={() => handleSync(integration)}
                        tooltip="Synchronize data"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </ButtonWithTooltip>
                    )}
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
          {addIntegrationButton}
        </div>
      )}

      <AddEditIntegrationModal
        dataSetId={dataSetId}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSuccess={loadIntegrations}
        integrationTypeName={modalTypeName}
        integration={integrationToEdit}
      />

      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Integration</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Are you sure you want to delete this integration? This action cannot be undone.
              Products and documents imported by this integration will be deleted as well.
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
