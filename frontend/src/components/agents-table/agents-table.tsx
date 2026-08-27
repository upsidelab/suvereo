import { useState } from "react";
import { TableCell, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { useApplicationContext } from "@/lib/use-application-context";
import { AlertTriangle, Eye, Plus, Settings, Trash2 } from "lucide-react";

import { DeleteConfirmationModal } from "./delete-confirmation-modal";
import { useAgentTypes } from "./hooks/use-agent-types";
import { Agent, PaginatedResult } from "@/lib/types";
import { AgentFormModal } from "./agent-form-modal";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { ButtonWithTooltip } from "@/components/ui/button-with-tooltip.tsx";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip.tsx";
import { ApiError } from "@/lib/api-error.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";

const api = new ApiClient(authenticationProviderInstance);

export default function AgentsTable() {
  const { dataSetId, refetchAgents, hasDataSetPermission } = useApplicationContext()
    ?? { dataSetId: null, refetchAgents: async () => {}, hasDataSetPermission: () => false };
  const canAddAgents = hasDataSetPermission(PERMISSIONS.AGENT.ADD);
  const canChangeAgents = hasDataSetPermission(PERMISSIONS.AGENT.CHANGE);
  const canDeleteAgents = hasDataSetPermission(PERMISSIONS.AGENT.DELETE);
  const { agentTypes, loadingTypes } = useAgentTypes(canAddAgents || canChangeAgents);

  const [isAccessDenied, setIsAccessDenied] = useState(false);
  
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [isViewingAgent, setIsViewingAgent] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [agentToDelete, setAgentToDelete] = useState<Agent | null>(null);

  const fetchAgents = async (): Promise<PaginatedResult<Agent> | undefined> => {
    if (dataSetId === null) {
      return;
    }

    try {
      const agents = await api.agents().getDatasetAvailableAgents(dataSetId);
      setIsAccessDenied(false);
      return {
        results: agents,
        count: agents.length
      };
    } catch (loadError) {
      if (loadError instanceof ApiError && [403, 404].includes(loadError.response.status)) {
        setIsAccessDenied(true);
        return undefined;
      }
      throw loadError;
    }
  }

  const openNew = () => {
    setEditingAgent(null);
    setIsViewingAgent(false);
    setFormModalOpen(true);
  };

  const openEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setIsViewingAgent(false);
    setFormModalOpen(true);
  };

  const openView = (agent: Agent) => {
    setEditingAgent(agent);
    setIsViewingAgent(true);
    setFormModalOpen(true);
  };

  const handleDelete = (agent: Agent) => {
    setAgentToDelete(agent);
    setDeleteModalOpen(true);
  };

  const handleFormSuccess = async () => {
    setFormModalOpen(false);
    await refetchAgents();
  };

  const handleFormClose = (open: boolean) => {
    if (!open) {
      setFormModalOpen(false);
      setEditingAgent(null);
      setIsViewingAgent(false);
    }
  };

  const handleDeleteSuccess = async () => {
    setDeleteModalOpen(false);
    setAgentToDelete(null);
    await refetchAgents();
  };

  return (
    <>
      {canAddAgents && (
        <div className="flex items-center justify-end mb-6">
          <Button onClick={openNew}><Plus className="h-4 w-4"/>New agent</Button>
        </div>
      )}

      {isAccessDenied ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-500">You don't have permission to view this data set's agents.</p>
        </div>
      ) : (
        <PaginatedTable
          loadItems={fetchAgents}
          itemsReloadDependencies={1}
          noItemsMessage="You haven't configured any agents yet"
          tableHeaders={["Name", "Description", "Type", "Action"]}
          tableRow={(item, index) => {
            return (<TableRow key={index}>
              <TableCell>
                <div className="flex items-center gap-2">
                  {item.corrupted && <AlertTriangle className="h-4 w-4 text-yellow-500" />}
                  <span className={item.corrupted ? "text-muted-foreground" : ""}>
                      {item.name}
                    </span>
                </div>
              </TableCell>
              <TableCell className="max-w-[200px]">
                {item.description ? (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="truncate cursor-default">
                          {item.description}
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-sm">
                        <p className="whitespace-pre-wrap">{item.description}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell className={"w-1/4"}>
                {item.agent_type_name || agentTypes.find(t => t.key === item.agent_type)?.name || item.agent_type || 'Unknown'}
              </TableCell>
              <TableCell className="text-right w-1">
                <div className="flex justify-end space-x-2">
                  {!canChangeAgents && (
                    <ButtonWithTooltip
                      variant="outline"
                      size="sm"
                      onClick={() => openView(item)}
                      tooltip="View configuration"
                    >
                      <Eye className="h-4 w-4"/>
                    </ButtonWithTooltip>
                  )}
                  {canChangeAgents && (
                    <ButtonWithTooltip
                      variant="outline"
                      size="sm"
                      onClick={() => openEdit(item)}
                      tooltip="Settings"
                    >
                      <Settings className="h-4 w-4"/>
                    </ButtonWithTooltip>
                  )}
                  {canDeleteAgents && (
                    <ButtonWithTooltip
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(item)}
                      tooltip="Delete"
                    >
                      <Trash2 className="h-4 w-4"/>
                    </ButtonWithTooltip>
                  )}
                </div>
              </TableCell>
            </TableRow>)
          }}
        />
      )}

      <AgentFormModal
        open={formModalOpen}
        onOpenChange={handleFormClose}
        agent={editingAgent}
        agentTypes={agentTypes}
        loadingTypes={loadingTypes}
        dataSetId={dataSetId}
        onSuccess={handleFormSuccess}
        readOnly={isViewingAgent}
      />

      <DeleteConfirmationModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        agent={agentToDelete}
        onConfirm={handleDeleteSuccess}
      />
    </>
  );
}
