import { ReactNode, useState, useEffect, useMemo, useRef } from "react";
import { ApplicationContext, ApplicationContextValue } from "@/lib/application-context.ts";
import { Account } from "@/lib/types.ts";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { useLocation, useRouteLoaderData } from "react-router-dom";
import { ROOT_ROUTE_ID, RootRouteData } from "@/lib/root-route.ts";
import { PERMISSIONS } from "@/lib/permissions.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface ApplicationContextProviderProps {
  children: ReactNode;
}

function extractDataSetIdFromPath(path: string): number | null {
  const match = path.match(/\/data-sets\/(\d+)/);
  return match ? parseInt(match[1]) : null;
}

export function ApplicationContextProvider({ children }: ApplicationContextProviderProps) {
  // Onboarding mounts this provider outside the root route, where there is no loader data - and no
  // data sets either, since that is the only way onboarding is reached.
  const rootData = useRouteLoaderData(ROOT_ROUTE_ID) as RootRouteData | undefined;
  const dataSets = useMemo(() => rootData?.dataSets ?? [], [rootData]);
  const [dataSetId, setDataSetId] = useState<number | null>(null);
  const [availableAgents, setAvailableAgents] = useState<{ name: string; id: number; }[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [account, setAccount] = useState<Account | null>(null);
  const [supportedFileExtensions, setSupportedFileExtensions] = useState<string[]>([]);
  const [isLoadingFileExtensions, setIsLoadingFileExtensions] = useState(true);
  const [fileExtensionsError, setFileExtensionsError] = useState<string | null>(null);
  const hasFetchedFileExtensions = useRef(false);
  const location = useLocation();

  useEffect(() => {
    if (dataSets.length === 0) {
      return;
    }

    const urlDataSetId = extractDataSetIdFromPath(location.pathname);
    if (urlDataSetId && dataSets.some(dataSet => dataSet.id === urlDataSetId)) {
      setDataSetId(urlDataSetId);
      return;
    }

    if (dataSetId === null) {
      setDataSetId(dataSets[0].id!);
    }
  }, [location.pathname, dataSets, dataSetId]);

  const fetchAgentsForDataSet = async () => {
    const dataSet = dataSets.find(candidate => candidate.id === dataSetId);
    if (!dataSet?.permissions.includes(PERMISSIONS.AGENT.VIEW)) {
      setAvailableAgents([]);
      setIsLoadingAgents(false);
      return;
    }

    setIsLoadingAgents(true);
    try {
      const agents = await api.agents().getDatasetAvailableAgents(dataSet.id!);
      setAvailableAgents(agents.filter(agent => !agent.corrupted));
    } catch (error) {
      console.error("Failed to load agents:", error);
      setAvailableAgents([]);
    } finally {
      setIsLoadingAgents(false);
    }
  };

  useEffect(() => {
    fetchAgentsForDataSet();
  }, [dataSetId]);

  useEffect(() => {
    const fetchSupportedFileExtensions = async () => {
      if (hasFetchedFileExtensions.current) return;
      hasFetchedFileExtensions.current = true;

      try {
        const supportedTypes = await api.conversations().getSupportedFileTypes();
        setSupportedFileExtensions(supportedTypes.supported_extensions);
        setFileExtensionsError(null);
      } catch (error) {
        console.error('Failed to fetch supported file types:', error);
        setSupportedFileExtensions([]);
        setFileExtensionsError('Failed to load supported file types');
      } finally {
        setIsLoadingFileExtensions(false);
      }
    };

    fetchSupportedFileExtensions();
  }, []);

  const value: ApplicationContextValue = {
    dataSets,
    dataSetId,
    setDataSetId,
    availableAgents,
    setAvailableAgents,
    isLoadingAgents,
    setIsLoadingAgents,
    refetchAgents: fetchAgentsForDataSet,
    account,
    setAccount,
    supportedFileExtensions,
    setSupportedFileExtensions,
    isLoadingFileExtensions,
    setIsLoadingFileExtensions,
    fileExtensionsError,
    setFileExtensionsError
  };

  return (
    <ApplicationContext.Provider value={value}>
      {children}
    </ApplicationContext.Provider>
  );
}
