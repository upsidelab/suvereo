import { MissingPermission, PermissionEntity } from "@/lib/permissions/types.ts";
import { PermissionLabel } from "@/components/roles/permission-label.tsx";

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
  if (missingPermissions.length > 0) {
    return (
      <ul className="text-sm text-destructive mb-4 space-y-1.5">
        {missingPermissions.map((missing) => (
          <li key={missing.code}>
            <PermissionLabel code={missing.code} entities={entities} /> is required by{" "}
            {missing.required_by.map((code, index) => (
              <span key={code}>
                {index > 0 && ", "}
                <PermissionLabel code={code} entities={entities} />
              </span>
            ))}
          </li>
        ))}
      </ul>
    );
  }

  if (serverMessages.length === 0) {
    return null;
  }

  return (
    <ul className="text-sm text-destructive mb-4 space-y-1">
      {serverMessages.map((message) => <li key={message}>{message}</li>)}
    </ul>
  );
}
