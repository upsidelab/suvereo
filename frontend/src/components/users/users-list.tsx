import { useState } from "react";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { TableCell, TableRow } from "@/components/ui/table.tsx";
import { NewUserModal } from "@/components/users/new-user-modal.tsx";
import { EditUserModal } from "@/components/users/edit-user-modal.tsx";
import { ChangePasswordModal } from "@/components/users/change-password-modal.tsx";
import { Check } from "lucide-react";
import { User } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";
import { PERMISSIONS } from "@/lib/permissions.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

const api = new ApiClient(authenticationProviderInstance);

export function UsersList() {
  const { hasPermission } = useApplicationContext()!;
  const canAddUsers = hasPermission(PERMISSIONS.USER.ADD);
  const canChangeUsers = hasPermission(PERMISSIONS.USER.CHANGE);
  const [version, setVersion] = useState(0);
  const [isAccessDenied, setIsAccessDenied] = useState(false);

  const loadUsers = async (page: number) => {
    try {
      const result = await api.users().getUsers(page);
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
      {canAddUsers && (
        <div className="flex flex-col items-end mb-4">
          <NewUserModal onUserCreated={() => setVersion(version + 1)}/>
        </div>
      )}
      {isAccessDenied ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-500">You don't have permission to view users.</p>
        </div>
      ) : (
        <PaginatedTable<User>
          loadItems={loadUsers}
          itemsReloadDependencies={version}
          noItemsMessage="No users"
          tableHeaders={canChangeUsers ? ["Email", "Active", "Admin", "Actions"] : ["Email", "Active", "Admin"]}
          tableRow={(item, index) => {
            return (
              <TableRow key={index}>
                <TableCell width={canChangeUsers ? "70%" : "90%"}>{item.email}</TableCell>
                <TableCell width="5%">{item.isActive && <Check size={16} />}</TableCell>
                <TableCell width="5%">{item.isAdmin && <Check size={16} />}</TableCell>
                {canChangeUsers && (
                  <TableCell className="flex space-x-4" width="20%">
                    <EditUserModal user={item} onUserUpdated={() => setVersion(version + 1)} />
                    <ChangePasswordModal user={item} onUserUpdated={() => setVersion(version + 1)} />
                  </TableCell>
                )}
              </TableRow>
            )
          }}
        />
      )}
    </>
  )
}
