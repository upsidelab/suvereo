import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { PermissionEntity } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { MissingPermission, PermissionChecklist } from "@/components/roles/permission-checklist.tsx";
import { GroupMembersPanel } from "@/components/roles/groups/group-members-panel.tsx";
import { AdminMembersPanel } from "@/components/roles/groups/admin-members-panel.tsx";
import { ADMIN_ROLE, GlobalRole, isAdminRole } from "@/components/roles/groups/admin-role.ts";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type GroupFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

type Section = "permissions" | "members";

export interface GroupModalProps {
  role?: GlobalRole;
  onSaved: () => void;
}

export function GroupModal({ role, onSaved }: GroupModalProps) {
  const { account } = useApplicationContext()!;
  const isAdmin = !!account?.isAdmin;
  const isBuiltIn = isAdminRole(role);
  const canEdit = isAdmin && !isBuiltIn;

  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<Section>("permissions");
  const [entities, setEntities] = useState<PermissionEntity[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
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
    setSection("permissions");

    api.permissions().getPermissions("global").then(setEntities).catch(() => setEntities([]));

    if (isBuiltIn) {
      setSelected([]);
      form.reset({ name: ADMIN_ROLE.name });
    } else if (role?.id != null) {
      api.groups().getGroupDetail(role.id).then((detail) => {
        form.reset({ name: detail.name });
        setSelected(detail.permissions);
      }).catch(() => setError("Could not load this role."));
    } else {
      form.reset({ name: "" });
      setSelected([]);
    }
  }, [open, role, isBuiltIn, form]);

  const handleSubmit = async (values: GroupFormSchema) => {
    setError(null);
    setPermissionErrors([]);
    setMissingPermissions([]);

    const response = role?.id != null
      ? await api.groups().updateGroup(role.id, values.name, selected)
      : await api.groups().createGroup(values.name, selected);

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

  const triggerLabel = role ? (canEdit ? "Edit" : "View") : "New Role";
  const title = role
    ? (canEdit ? `Edit role ${role.name}` : `Role ${role.name}`)
    : "New Role";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={role ? "secondary" : "default"}>{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {error && <p className="text-sm text-destructive mb-4">{error}</p>}
        {permissionErrors.length > 0 && (
          <ul className="text-sm text-destructive mb-4 space-y-1">
            {permissionErrors.map((message) => <li key={message}>{message}</li>)}
          </ul>
        )}
        <div className="flex items-center space-x-2 border-b pb-2 mb-4">
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

        {section === "permissions" && (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
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
              {!isBuiltIn && !isAdmin && (
                <p className="text-sm text-muted-foreground">Only an admin can edit a role's permissions.</p>
              )}

              <PermissionChecklist
                entities={entities}
                selected={isBuiltIn
                  ? entities.flatMap((entity) => entity.permissions.map((permission) => permission.code))
                  : selected}
                onChange={setSelected}
                disabled={!canEdit}
                missingPermissions={missingPermissions}
              />

              {canEdit && <Button type="submit">Save</Button>}
            </form>
          </Form>
        )}

        {section === "members" && (
          isBuiltIn
            ? <AdminMembersPanel />
            : role?.id != null
              ? <GroupMembersPanel groupId={role.id} />
              : <p className="text-sm text-muted-foreground">Save the role first to add members.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
