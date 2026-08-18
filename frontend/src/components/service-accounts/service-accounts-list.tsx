import { useState } from "react";
import { TableCell, TableRow } from "@/components/ui/table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { ServiceAccount } from "@/lib/types.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { EditServiceAccountModal } from "./edit-service-account-modal.tsx";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { Check } from "lucide-react";
import { NewServiceAccountModal } from "@/components/service-accounts/new-service-account-modal.tsx";
import { TokenResetModal } from "@/components/service-accounts/token-reset-modal.tsx";
import { ApiError } from "@/lib/api-error.ts";
import { PERMISSIONS } from "@/lib/permissions.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

const api = new ApiClient(authenticationProviderInstance);

export function ServiceAccountsList() {
  const { hasPermission } = useApplicationContext()!;
  const canAddServiceAccounts = hasPermission(PERMISSIONS.SERVICE_ACCOUNT.ADD);
  const canChangeServiceAccounts = hasPermission(PERMISSIONS.SERVICE_ACCOUNT.CHANGE);
  const [version, setVersion] = useState(0);
  const [isAccessDenied, setIsAccessDenied] = useState(false);

  const loadServiceAccounts = async (page: number) => {
    try {
      const result = await api.serviceAccounts().getServiceAccounts(page);
      setIsAccessDenied(false);
      return result;
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.response.status === 403) {
        setIsAccessDenied(true);
        return undefined;
      }
      throw loadError;
    }
  }

  return (
    <>
      {canAddServiceAccounts && (
        <div className="flex flex-col items-end mb-4">
          <NewServiceAccountModal onServiceAccountCreated={() => setVersion(version + 1)} />
        </div>
      )}
      {isAccessDenied ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-500">You don't have permission to view service accounts.</p>
        </div>
      ) : (
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
                  {canChangeServiceAccounts &&
                    <EditServiceAccountModal
                      serviceAccount={item}
                      onServiceAccountUpdated={() => setVersion(version + 1)}
                    />
                  }
                  {canChangeServiceAccounts && <TokenResetModal serviceAccount={item} />}
                </TableCell>
              </TableRow>
            )
          }}
        />
      )}
    </>
  );
}
