import { useContext } from "react";
import { ApplicationContext } from "@/lib/application-context.ts";

export function useApplicationContext() {
  const context = useContext(ApplicationContext);

  const currentDataSet = context?.dataSets.find((dataSet) => dataSet.id === context.dataSetId);

  // Single source of truth for "does this identity hold codename X" -- callers pass a
  // permission codename instead of reaching into account.permissions/currentDataSet.permissions
  // themselves. Mirrors has_dataset_perm on the backend: the account/dataset serializers already
  // fold Admin/global-counterpart capability into these arrays, so no isAdmin fallback is needed
  // here for anything with a real permission codename.
  const hasPermission = (codename: string): boolean => !!context?.account?.permissions.includes(codename);

  // dataSetId defaults to the globally selected data set (context.dataSetId), but some views
  // (e.g. a data set's own settings pages) work against a data set from the URL that need not
  // match it -- pass that data set's id explicitly in those cases.
  const hasDatasetPermission = (codename: string, dataSetId?: number): boolean => {
    const dataSet = dataSetId === undefined ? currentDataSet : context?.dataSets.find((ds) => ds.id === dataSetId);
    return !!dataSet?.permissions.includes(codename);
  };

  return context ? { ...context, currentDataSet, hasPermission, hasDatasetPermission } : null;
}
