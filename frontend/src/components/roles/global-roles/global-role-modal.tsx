import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Separator } from "@/components/ui/separator.tsx";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { MissingPermission, PermissionEntity } from "@/lib/permissions/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { PermissionChecklist } from "@/components/roles/permission-checklist.tsx";
import { PermissionErrors } from "@/components/roles/permission-errors.tsx";
import { GlobalRoleMembersPanel } from "@/components/roles/global-roles/global-role-members-panel.tsx";
import { AdminMembersPanel } from "@/components/roles/global-roles/admin-members-panel.tsx";
import { ADMIN_ROLE, GlobalRole, isAdminRole } from "@/components/roles/global-roles/admin-role.ts";
import { PermissionEscalationDialog } from "@/components/roles/permission-escalation-dialog.tsx";
import { permissionEscalationWarnings } from "@/lib/permissions/escalation.ts";
import { missingDependencies, unresolvedRequirements } from "@/lib/permissions/dependencies.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type GroupFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

type Section = "permissions" | "members";

export interface GlobalRoleModalProps {
  role?: GlobalRole;
  onSaved: () => void;
}

export function GlobalRoleModal({ role, onSaved }: GlobalRoleModalProps) {
  const { hasPermission } = useApplicationContext()!;
  const isBuiltIn = isAdminRole(role);
  const canEdit = role
    ? hasPermission(PERMISSIONS.GLOBAL_ROLE.CHANGE) && !isBuiltIn
    : hasPermission(PERMISSIONS.GLOBAL_ROLE.ADD);

  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<Section>("permissions");
  const [entities, setEntities] = useState<PermissionEntity[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [storedPermissions, setStoredPermissions] = useState<string[]>([]);
  const [pendingValues, setPendingValues] = useState<GroupFormSchema | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [permissionErrors, setPermissionErrors] = useState<string[]>([]);
  const [missingPermissions, setMissingPermissions] = useState<MissingPermission[]>([]);

  const form = useForm<GroupFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: role?.name ?? ""
    }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    setPermissionErrors([]);
    setMissingPermissions([]);
    setPendingValues(null);
    setSection("permissions");

    api.permissions().getPermissions("global").then(setEntities).catch(() => setEntities([]));

    if (isBuiltIn) {
      setSelected([]);
      setStoredPermissions([]);
      form.reset({ name: ADMIN_ROLE.name });
    } else if (role?.id != null) {
      api.globalRoles().getGlobalRoleDetail(role.id).then((detail) => {
        form.reset({ name: detail.name });
        setSelected(detail.permissions);
        setStoredPermissions(detail.permissions);
      }).catch(() => setError("Could not load this role."));
    } else {
      form.reset({ name: "" });
      setSelected([]);
      setStoredPermissions([]);
    }
  }, [open, role, isBuiltIn, form]);

  useEffect(() => {
    setMissingPermissions((reported) => unresolvedRequirements(reported, selected));
  }, [selected]);

  const warnings = permissionEscalationWarnings(selected, storedPermissions);

  const save = async (values: GroupFormSchema) => {
    setPendingValues(null);
    setError(null);
    setPermissionErrors([]);
    setMissingPermissions([]);

    const response = role?.id != null
      ? await api.globalRoles().updateGlobalRole(role.id, values.name, selected)
      : await api.globalRoles().createGlobalRole(values.name, selected);

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      if (Array.isArray(body.permissions)) setPermissionErrors(body.permissions);
      if (Array.isArray(body.missing_permissions)) setMissingPermissions(body.missing_permissions);
      if (Array.isArray(body.name)) form.setError("name", { message: body.name[0] });
      if (!body.permissions && !body.name) setError(body.detail ?? "Could not save this role.");
      return;
    }

    setOpen(false);
    onSaved();
  };

  const handleSubmit = (values: GroupFormSchema) => {
    const missing = missingDependencies(selected, entities);
    if (missing.length > 0) {
      setError(null);
      setPermissionErrors([]);
      setMissingPermissions(missing);
      return;
    }
    if (warnings.length > 0) {
      setPendingValues(values);
      return;
    }
    return save(values);
  };

  const triggerLabel = role ? (canEdit ? "Edit" : "View") : "New global role";
  const title = role
    ? (canEdit ? `Edit global role ${role.name}` : `Global role ${role.name}`)
    : "New global role";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={role ? "secondary" : "default"}>{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent className="w-[min(92vw,36rem)] max-w-none">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {error && <p className="text-sm text-destructive mb-4">{error}</p>}
        <PermissionErrors
          entities={entities}
          missingPermissions={missingPermissions}
          serverMessages={permissionErrors}
        />
        <div className="flex items-center space-x-2 border-b pb-2">
          <Button
            type="button"
            variant={section === "permissions" ? "default" : "ghost"}
            onClick={() => setSection("permissions")}
          >
            Permissions
          </Button>
          <Button
            type="button"
            variant={section === "members" ? "default" : "ghost"}
            onClick={() => setSection("members")}
          >
            Members
          </Button>
        </div>

        {/* Both sections share a fixed height, so switching between them cannot resize the dialog. */}
        <div className="h-[min(62vh,34rem)] flex flex-col">
        {section === "permissions" && (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="flex grow flex-col space-y-4 min-h-0">
              {canEdit ? (
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Role name" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              ) : null}

              {isBuiltIn && (
                <p className="text-sm text-muted-foreground">
                  Admins have full access to the system. This can't be edited.
                </p>
              )}
              {!isBuiltIn && !canEdit && (
                <p className="text-sm text-muted-foreground">You can't edit this role's permissions.</p>
              )}

              <Separator />

              <div className="flex grow flex-col space-y-2 min-h-0 pt-4">
                <p className="text-sm font-medium leading-none">Permissions</p>
                <PermissionChecklist
                  entities={entities}
                  selected={isBuiltIn
                    ? entities.flatMap((entity) => entity.permissions.map((permission) => permission.code))
                    : selected}
                  onChange={setSelected}
                  disabled={!canEdit}
                  missingPermissions={missingPermissions}
                  className="h-auto grow min-h-0"
                />
              </div>

              {canEdit && (
                <div className="flex justify-end">
                  <Button type="submit">Save</Button>
                </div>
              )}
            </form>
          </Form>
        )}

        <PermissionEscalationDialog
          open={pendingValues !== null}
          warnings={warnings}
          entities={entities}
          onConfirm={() => { if (pendingValues) void save(pendingValues); }}
          onCancel={() => setPendingValues(null)}
        />

        {section === "members" && (
          isBuiltIn
            ? <AdminMembersPanel />
            : role?.id != null
              ? <GlobalRoleMembersPanel globalRoleId={role.id} />
              : <p className="text-sm text-muted-foreground">Save the role first to add members.</p>
        )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
