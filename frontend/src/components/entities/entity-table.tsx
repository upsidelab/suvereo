import { useCallback } from "react";
import { TableCell, TableRow } from "@/components/ui/table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { EntityType } from "@/lib/types.ts";

const api = new ApiClient();

interface EntityTableProps {
  dataSetId: number;
  entityType: EntityType;
}

export function EntityTable({ dataSetId, entityType }: EntityTableProps) {
  const loadRecords = useCallback(
    (page: number) => api.entities().getRecords(dataSetId, entityType.slug, page),
    [dataSetId, entityType.slug],
  );

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
