import { useState, useEffect } from "react";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { ToolProvidingIntegrationOption } from "@/lib/types";

const apiClient = new ApiClient(authenticationProviderInstance);

export function useToolProvidingIntegrationOptions(dataSetId: number | null, enabled: boolean) {
  const [toolProvidingIntegrationOptions, setToolProvidingIntegrationOptions] = useState<ToolProvidingIntegrationOption[]>([]);
  const [loadingToolProvidingIntegrations, setLoadingToolProvidingIntegrations] = useState(false);
  const [toolProvidingIntegrationsFailed, setToolProvidingIntegrationsFailed] = useState(false);

  useEffect(() => {
    setToolProvidingIntegrationOptions([]);
    setToolProvidingIntegrationsFailed(false);
    if (!enabled || !dataSetId) return;

    let stale = false;
    const fetchToolProvidingIntegrationOptions = async () => {
      setLoadingToolProvidingIntegrations(true);
      try {
        const options = await apiClient.agents().getToolProvidingIntegrations(dataSetId);
        if (!stale) setToolProvidingIntegrationOptions(options);
      } catch (error) {
        console.error('Failed to fetch tool-providing integrations:', error);
        if (!stale) setToolProvidingIntegrationsFailed(true);
      } finally {
        if (!stale) setLoadingToolProvidingIntegrations(false);
      }
    };

    fetchToolProvidingIntegrationOptions();
    return () => {
      stale = true;
    };
  }, [dataSetId, enabled]);

  return { toolProvidingIntegrationOptions, loadingToolProvidingIntegrations, toolProvidingIntegrationsFailed };
}
