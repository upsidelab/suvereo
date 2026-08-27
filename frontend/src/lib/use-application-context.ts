import { useContext } from "react";
import { ApplicationContext } from "@/lib/application-context.ts";

export function useApplicationContext() {
  const context = useContext(ApplicationContext);
  const currentDataSet = context?.dataSets.find((dataSet) => dataSet.id === context.dataSetId);

  const hasPermission = (code: string): boolean => !!context?.account?.permissions.includes(code);

  const hasDataSetPermission = (code: string, dataSetId?: number): boolean => {
    const dataSet = dataSetId === undefined ? currentDataSet : context?.dataSets.find((ds) => ds.id === dataSetId);
    return !!dataSet?.permissions.includes(code);
  };

  return context ? { ...context, currentDataSet, hasPermission, hasDataSetPermission } : null;
}
