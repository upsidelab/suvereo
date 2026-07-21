import { ApiClient } from "@/lib/api.ts";
import { PaginatedTable } from "@/components/util/paginated-table.tsx";
import { TableCell, TableRow } from "@/components/ui/table.tsx";
import { useState } from "react";
import { NewUserModal } from "@/components/users/new-user-modal.tsx";
import { EditUserModal } from "@/components/users/edit-user-modal.tsx";
import { ChangePasswordModal } from "@/components/users/change-password-modal.tsx";
import { Check } from "lucide-react";
import { User } from "@/lib/types.ts";
import { ApiError } from "@/lib/api-error.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

const api = new ApiClient();

export function UsersList() {
  const { hasPermission } = useApplicationContext()!;
  const [version, setVersion] = useState(0);
  const [accessDenied, setAccessDenied] = useState(false);
  const canManageUsers = hasPermission("account.manage_users");

  const loadUsers = async (page: number) => {
    try {
      const result = await api.users().getUsers(page);
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
        <p className="text-lg font-medium text-gray-500">You don't have permission to view users.</p>
      </div>
    );
  }

  return (
    <>
      {canManageUsers && (
        <div className="flex flex-col items-end mb-4">
          <NewUserModal onUserCreated={() => setVersion(version + 1)}/>
        </div>
      )}
      <PaginatedTable<User>
        loadItems={loadUsers}
        itemsReloadDependencies={version}
        noItemsMessage="No users"
        tableHeaders={["Email", "Active", "Admin", "Actions"]}
        tableRow={(item, index) => {
          return (
            <TableRow key={index}>
              <TableCell width="70%">{item.email}</TableCell>
              <TableCell width="5%">{item.isActive && <Check size={16} />}</TableCell>
              <TableCell width="5%">{item.isAdmin && <Check size={16} />}</TableCell>
              <TableCell className="flex space-x-4" width="20%">
                {canManageUsers && <EditUserModal user={item} onUserUpdated={() => setVersion(version + 1)} />}
                {canManageUsers && <ChangePasswordModal user={item} onUserUpdated={() => setVersion(version + 1)} />}
              </TableCell>
            </TableRow>
          )
        }}
      />
    </>
  )
}
