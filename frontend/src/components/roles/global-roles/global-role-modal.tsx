import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Textarea } from "@/components/ui/textarea.tsx";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { MissingPermission, PermissionEntity } from "@/lib/permissions/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { PermissionChecklist } from "@/components/roles/permission-checklist.tsx";
import { PermissionErrors } from "@/components/roles/permission-errors.tsx";
import { ModalSection, ModalSections } from "@/components/roles/modal-sections.tsx";
import { ModalScrollArea } from "@/components/roles/modal-scroll-area.tsx";
import { GlobalRoleMembersPanel } from "@/components/roles/global-roles/global-role-members-panel.tsx";
import { AdminMembersPanel } from "@/components/roles/global-roles/admin-members-panel.tsx";
import { ADMIN_ROLE, GlobalRole, isAdminRole } from "@/components/roles/global-roles/admin-role.ts";
import { PermissionEscalationDialog } from "@/components/roles/permission-escalation-dialog.tsx";
import { permissionEscalationRisks } from "@/lib/permissions/escalation.ts";
import { missingDependencies, unresolvedRequirements } from "@/lib/permissions/dependencies.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";

const formSchema = z.object({
  name: z.string().trim().min(1),
  description: z.string().trim(),
});
type GroupFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

type Section = "details" | "permissions" | "members";

const SECTIONS: readonly ModalSection<Section>[] = [
  { key: "details", label: "Details" },
  { key: "permissions", label: "Permissions" },
  { key: "members", label: "Members" },
];

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
  const [section, setSection] = useState<Section>("details");
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
      name: role?.name ?? "",
      description: role?.description ?? ""
    }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    setPermissionErrors([]);
    setMissingPermissions([]);
    setPendingValues(null);
    setSection("details");

    api.permissions().getPermissions("global").then(setEntities).catch(() => setEntities([]));

    if (isBuiltIn) {
      setSelected([]);
      setStoredPermissions([]);
      form.reset({ name: ADMIN_ROLE.name, description: ADMIN_ROLE.description ?? "" });
    } else if (role?.id != null) {
      api.globalRoles().getGlobalRoleDetail(role.id).then((detail) => {
        form.reset({ name: detail.name, description: detail.description });
        setSelected(detail.permissions);
        setStoredPermissions(detail.permissions);
      }).catch(() => setError("Could not load this role."));
    } else {
      form.reset({ name: "", description: "" });
      setSelected([]);
      setStoredPermissions([]);
    }
  }, [open, role, isBuiltIn, form]);

  useEffect(() => {
    setMissingPermissions((reported) => unresolvedRequirements(reported, selected));
  }, [selected]);

  const risks = permissionEscalationRisks(selected, storedPermissions);

  const save = async (values: GroupFormSchema) => {
    setPendingValues(null);
    setError(null);
    setPermissionErrors([]);
    setMissingPermissions([]);

    const response = role?.id != null
      ? await api.globalRoles().updateGlobalRole(role.id, values.name, values.description, selected)
      : await api.globalRoles().createGlobalRole(values.name, values.description, selected);

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      if (Array.isArray(body.permissions)) setPermissionErrors(body.permissions);
      if (Array.isArray(body.missing_permissions)) setMissingPermissions(body.missing_permissions);
      if (body.permissions || body.missing_permissions) {
        setSection("permissions");
      } else if (body.name || body.description) {
        setSection("details");
      }
      if (Array.isArray(body.name)) form.setError("name", { message: body.name[0] });
      if (Array.isArray(body.description)) form.setError("description", { message: body.description[0] });
      if (!body.permissions && !body.name && !body.description) setError(body.detail ?? "Could not save this role.");
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
      setSection("permissions");
      return;
    }
    if (risks.length > 0) {
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
        <ModalSections sections={SECTIONS} active={section} onChange={setSection} />

        {/* Fixed height, so switching sections cannot resize the dialog. */}
        <div className="h-[min(62vh,34rem)] flex flex-col">
        {section !== "members" && (
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit, () => setSection("details"))}
              className="flex grow flex-col space-y-4 min-h-0"
            >
              {section === "details" && (
                <ModalScrollArea className="flex flex-col space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Role name" disabled={!canEdit} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Description"
                            rows={4}
                            className="resize-y"
                            disabled={!canEdit}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {isBuiltIn && (
                    <p className="text-sm text-muted-foreground">
                      Admins have full access to the system. This can't be edited.
                    </p>
                  )}
                  {!isBuiltIn && !canEdit && (
                    <p className="text-sm text-muted-foreground">You can't edit this role's details.</p>
                  )}
                </ModalScrollArea>
              )}

              {section === "permissions" && (
                <div className="flex grow flex-col min-h-0">
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
              )}

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
          risks={risks}
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
