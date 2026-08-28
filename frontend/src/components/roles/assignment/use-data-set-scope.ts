import { useState } from "react";
import { DataSet } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

export interface DataSetScopeMessages {
  /** The access listing is gated on assign, so there is no read-only view. */
  needsAssign: string;
  noDataSets: string;
  unselected: string;
  empty: string;
}

export interface DataSetScope {
  dataSets: DataSet[];
  dataSetId: number | null;
  setDataSetId: (dataSetId: number) => void;
  showSelector: boolean;
  /** Assign held and a data set chosen. */
  isReady: boolean;
  message: (messages: DataSetScopeMessages) => string;
}

export function useDataSetScope(canAssign: boolean): DataSetScope {
  const { dataSets } = useApplicationContext()!;
  const [dataSetId, setDataSetId] = useState<number | null>(null);

  return {
    dataSets,
    dataSetId,
    setDataSetId,
    showSelector: canAssign && dataSets.length > 0,
    isReady: canAssign && dataSetId !== null,
    message: (messages) => {
      if (!canAssign) return messages.needsAssign;
      if (dataSets.length === 0) return messages.noDataSets;
      if (dataSetId === null) return messages.unselected;
      return messages.empty;
    },
  };
}
