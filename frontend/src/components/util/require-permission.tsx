import { ReactNode } from "react";
import { useParams } from "react-router-dom";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { NotFound } from "@/pages/not-found.tsx";

export interface RequirePermissionProps {
  globalAnyOf?: string[];
  dataSetAnyOf?: string[];
  dataSetAccess?: boolean;
  children: ReactNode;
}

/**
 * Renders `children` only when the account holds the permissions the route needs, and the
 * not-found page otherwise. Reads the permissions the application context already loaded, so
 * gating a route costs no extra requests, and the page it guards never mounts - nothing fetches
 * on behalf of a user who cannot see it.
 *
 * @param globalAnyOf Global codes; holding any one of them is enough.
 * @param dataSetAnyOf Codes on the data set named by the route; holding any one of them is enough.
 * @param dataSetAccess Requires only that the data set named by the route is one the user can see.
 */
export function RequirePermission({ globalAnyOf, dataSetAnyOf, dataSetAccess, children }: RequirePermissionProps) {
  const { account, dataSets, isLoadingDataSets, hasPermission, hasDatasetPermission } = useApplicationContext()!;
  const { id, dataSetId } = useParams();

  if (!account || isLoadingDataSets) {
    return null;
  }

  if (globalAnyOf && !globalAnyOf.some(permission => hasPermission(permission))) {
    return <NotFound />;
  }

  if (dataSetAnyOf || dataSetAccess) {
    const routeDataSetId = Number(dataSetId ?? id);
    if (!dataSets.some(dataSet => dataSet.id === routeDataSetId)) {
      return <NotFound />;
    }
    if (dataSetAnyOf && !dataSetAnyOf.some(permission => hasDatasetPermission(permission, routeDataSetId))) {
      return <NotFound />;
    }
  }

  return <>{children}</>;
}
