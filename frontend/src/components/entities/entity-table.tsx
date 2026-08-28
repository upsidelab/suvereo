import { useCallback, useState } from "react";
import { TableCell, TableRow } from "@/components/ui/table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { EntityType } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";

const api = new ApiClient(authenticationProviderInstance);

interface EntityTableProps {
  dataSetId: number;
  entityType: EntityType;
}

export function EntityTable({ dataSetId, entityType }: EntityTableProps) {
  const [isAccessDenied, setIsAccessDenied] = useState(false);

  const loadRecords = useCallback(
    async (page: number) => {
      try {
        const result = await api.entities().getRecords(dataSetId, entityType.slug, page);
        setIsAccessDenied(false);
        return result;
      } catch (loadError) {
        if (loadError instanceof ApiError && [403, 404].includes(loadError.response.status)) {
          setIsAccessDenied(true);
          return undefined;
        }
        throw loadError;
      }
    },
    [dataSetId, entityType.slug],
  );

  if (isAccessDenied) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-medium text-gray-500">
          You don't have access to this data set's {entityType.label.toLowerCase()}.
        </p>
      </div>
    );
  }

  return (
    <PaginatedTable<Record<string, unknown>>
      loadItems={loadRecords}
      noItemsMessage={`No ${entityType.label.toLowerCase()} found`}
      tableHeaders={entityType.fields.map(f => f.label)}
      tableRow={(record, index) => (
        <TableRow key={index}>
          {entityType.fields.map(field => (
            <TableCell key={field.name}>{String(record[field.name] ?? "")}</TableCell>
          ))}
        </TableRow>
      )}
    />
  );
}
