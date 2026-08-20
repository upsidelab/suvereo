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
import { DatasetRoleOption, PermissionEntity } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { MissingPermission, PermissionChecklist } from "@/components/roles/permission-checklist.tsx";
import { PermissionErrors } from "@/components/roles/permission-errors.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type DatasetRoleFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

export interface DatasetRoleModalProps {
  role?: DatasetRoleOption;
  onSaved: () => void;
}

export function DatasetRoleModal({ role, onSaved }: DatasetRoleModalProps) {
  const { account } = useApplicationContext()!;
  const isAdmin = !!account?.isAdmin;
  const [open, setOpen] = useState(false);
  const [entities, setEntities] = useState<PermissionEntity[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [permissionErrors, setPermissionErrors] = useState<string[]>([]);
  const [missingPermissions, setMissingPermissions] = useState<MissingPermission[]>([]);

  const form = useForm<DatasetRoleFormSchema>({
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

    api.permissions().getPermissions("dataset").then(setEntities).catch(() => setEntities([]));

    if (role) {
      api.datasetRoles().getDatasetRoleDetail(role.id).then((detail) => {
        form.reset({ name: detail.name });
        setSelected(detail.permissions);
      }).catch(() => setError("Could not load this role."));
    } else {
      form.reset({ name: "" });
      setSelected([]);
    }
  }, [open, role, form]);

  const handleSubmit = async (values: DatasetRoleFormSchema) => {
    setError(null);
    setPermissionErrors([]);
    setMissingPermissions([]);

    const response = role
      ? await api.datasetRoles().updateDatasetRole(role.id, values.name, selected)
      : await api.datasetRoles().createDatasetRole(values.name, selected);

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

  const triggerLabel = role ? (isAdmin ? "Edit" : "View") : "New Role";
  const title = role ? (isAdmin ? `Edit role ${role.name}` : `Role ${role.name}`) : "New Dataset Role";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={role ? "secondary" : "default"}>{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent className="w-[min(92vw,36rem)] max-w-none">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground -mt-2 mb-2">
          This only defines the role. To grant it to a user or group, go to Data Sets → Manage Access for that data set.
        </p>
        {error && <p className="text-sm text-destructive mb-4">{error}</p>}
        <PermissionErrors
          entities={entities}
          missingPermissions={missingPermissions}
          serverMessages={permissionErrors}
        />
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            {isAdmin ? (
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
              <p className="text-sm text-muted-foreground">Only an admin can edit a role's permissions.</p>
            )}
            <PermissionChecklist
              entities={entities}
              selected={selected}
              onChange={setSelected}
              disabled={!isAdmin}
              missingPermissions={missingPermissions}
            />
            {isAdmin && <Button type="submit">Save</Button>}
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
