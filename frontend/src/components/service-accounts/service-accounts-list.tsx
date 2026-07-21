import { useState } from "react";
import { TableCell, TableRow } from "@/components/ui/table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { ServiceAccount } from "@/lib/types.ts";
import { EditServiceAccountModal } from "./edit-service-account-modal.tsx";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { Check } from "lucide-react";
import { NewServiceAccountModal } from "@/components/service-accounts/new-service-account-modal.tsx";
import { TokenResetModal } from "@/components/service-accounts/token-reset-modal.tsx";
import { ApiError } from "@/lib/api-error.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

const api = new ApiClient();

export function ServiceAccountsList() {
  const { hasPermission } = useApplicationContext()!;
  const [version, setVersion] = useState(0);
  const [accessDenied, setAccessDenied] = useState(false);
  const canManageServiceAccounts = hasPermission("account.manage_service_accounts");

  const loadServiceAccounts = async (page: number) => {
    try {
      const result = await api.serviceAccounts().getServiceAccounts(page);
      setAccessDenied(false);
      return result;
    } catch (err) {
      if (err instanceof ApiError && err.response.status === 403) {
        setAccessDenied(true);
        return undefined;
      }
      throw err;
    }
  }

  if (accessDenied) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-medium text-gray-500">You don't have permission to view service accounts.</p>
      </div>
    );
  }

  return (
    <>
      {canManageServiceAccounts && (
        <div className="flex flex-col items-end mb-4">
          <NewServiceAccountModal onServiceAccountCreated={() => setVersion(version + 1)} />
        </div>
      )}
      <PaginatedTable<ServiceAccount>
        loadItems={loadServiceAccounts}
        itemsReloadDependencies={version}
        noItemsMessage="No service accounts"
        tableHeaders={["Name", "Date Created", "Active", "Admin", "Actions"]}
        tableRow={(item, index) => {
          return (
            <TableRow key={index}>
              <TableCell width="60%">{item.email}</TableCell>
              <TableCell width="10%">{new Date(item.dateCreated).toLocaleDateString()}</TableCell>
              <TableCell width="5%">{item.isActive && <Check size={16} />}</TableCell>
              <TableCell width="5%">{item.isAdmin && <Check size={16} />}</TableCell>
              <TableCell className="flex space-x-4" width="20%">
                {canManageServiceAccounts && (
                  <EditServiceAccountModal serviceAccount={item} onServiceAccountUpdated={() => setVersion(version + 1)} />
                )}
                {canManageServiceAccounts && <TokenResetModal serviceAccount={item} />}
              </TableCell>
            </TableRow>
          )
        }}
      />
    </>
  );
}
