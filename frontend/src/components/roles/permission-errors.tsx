import { MissingPermission, PermissionEntity } from "@/lib/permissions/types.ts";
import { permissionName } from "@/lib/permissions/names.ts";

export interface PermissionErrorsProps {
  entities: PermissionEntity[];
  missingPermissions: MissingPermission[];
  serverMessages: string[];
}

/**
 * The rejected save, restated in the editor's own names. Falls back to what the server said for
 * anything the structured `missing_permissions` does not cover, such as a code the scope cannot
 * carry at all.
 */
export function PermissionErrors({ entities, missingPermissions, serverMessages }: PermissionErrorsProps) {
  const messages = missingPermissions.length > 0
    ? missingPermissions.map((missing) => {
      const requiredBy = missing.required_by.map((code) => permissionName(code, entities)).join(", ");
      return `${permissionName(missing.code, entities)} is required by ${requiredBy}.`;
    })
    : serverMessages;

  if (messages.length === 0) {
    return null;
  }

  return (
    <ul className="text-sm text-destructive mb-4 space-y-1">
      {messages.map((message) => <li key={message}>{message}</li>)}
    </ul>
  );
}
