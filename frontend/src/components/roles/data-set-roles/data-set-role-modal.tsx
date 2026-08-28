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
import { DataSetRoleOption } from "@/lib/types.ts";
import { MissingPermission, PermissionEntity } from "@/lib/permissions/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { PermissionChecklist } from "@/components/roles/permission-checklist.tsx";
import { PermissionErrors } from "@/components/roles/permission-errors.tsx";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { missingDependencies, unresolvedRequirements } from "@/lib/permissions/dependencies.ts";
import { ModalSection, ModalSections } from "@/components/roles/modal-sections.tsx";
import { DataSetRoleMembersPanel } from "@/components/roles/data-set-roles/data-set-role-members-panel.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type DataSetRoleFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

type DataSetRoleSection = "permissions" | "members";

const SECTIONS: readonly ModalSection<DataSetRoleSection>[] = [
  { key: "permissions", label: "Permissions" },
  { key: "members", label: "Members" },
];

export interface DataSetRoleModalProps {
  role?: DataSetRoleOption;
  onSaved: () => void;
}

export function DataSetRoleModal({ role, onSaved }: DataSetRoleModalProps) {
  const { hasPermission } = useApplicationContext()!;
  const canEdit = role
    ? hasPermission(PERMISSIONS.DATA_SET_ROLE.CHANGE)
    : hasPermission(PERMISSIONS.DATA_SET_ROLE.ADD);
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<DataSetRoleSection>("permissions");
  const [entities, setEntities] = useState<PermissionEntity[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [permissionErrors, setPermissionErrors] = useState<string[]>([]);
  const [missingPermissions, setMissingPermissions] = useState<MissingPermission[]>([]);

  const form = useForm<DataSetRoleFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: role?.name ?? ""
    }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSection("permissions");
    setPermissionErrors([]);
    setMissingPermissions([]);

    api.permissions().getPermissions("data_set").then(setEntities).catch(() => setEntities([]));

    if (role) {
      api.dataSetRoles().getDataSetRoleDetail(role.id).then((detail) => {
        form.reset({ name: detail.name });
        setSelected(detail.permissions);
      }).catch(() => setError("Could not load this role."));
    } else {
      form.reset({ name: "" });
      setSelected([]);
    }
  }, [open, role, form]);

  useEffect(() => {
    setMissingPermissions((reported) => unresolvedRequirements(reported, selected));
  }, [selected]);

  const save = async (values: DataSetRoleFormSchema) => {
    setError(null);
    setPermissionErrors([]);
    setMissingPermissions([]);

    const response = role
      ? await api.dataSetRoles().updateDataSetRole(role.id, values.name, selected)
      : await api.dataSetRoles().createDataSetRole(values.name, selected);

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

  const handleSubmit = (values: DataSetRoleFormSchema) => {
    const missing = missingDependencies(selected, entities);
    if (missing.length > 0) {
      setError(null);
      setPermissionErrors([]);
      setMissingPermissions(missing);
      return;
    }
    return save(values);
  };

  const triggerLabel = role ? (canEdit ? "Edit" : "View") : "New data set role";
  const title = role
    ? (canEdit ? `Edit data set role ${role.name}` : `Data set role ${role.name}`)
    : "New data set role";

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
                ) : (
                  <p className="text-sm text-muted-foreground">You can't edit this role's permissions.</p>
                )}
                <Separator />

                <div className="flex grow flex-col space-y-2 min-h-0 pt-4">
                  <p className="text-sm font-medium leading-none">Permissions</p>
                  <PermissionChecklist
                    entities={entities}
                    selected={selected}
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

          {section === "members" && (
            role
              ? <DataSetRoleMembersPanel roleId={role.id} />
              : <p className="text-sm text-muted-foreground">Save the role first to grant it to anyone.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
