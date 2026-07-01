import { TableCell, TableRow } from "@/components/ui/table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { EntityType } from "@/lib/types.ts";

const api = new ApiClient(authenticationProviderInstance);

interface EntityTableProps {
  dataSetId: number;
  entityType: EntityType;
}

export function EntityTable({ dataSetId, entityType }: EntityTableProps) {
  const loadRecords = async (page: number) => {
    return await api.entities().getRecords(dataSetId, entityType.slug, page);
  };

  return (
    <PaginatedTable<Record<string, unknown>>
      loadItems={loadRecords}
      itemsReloadDependencies={[dataSetId, entityType.slug]}
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
