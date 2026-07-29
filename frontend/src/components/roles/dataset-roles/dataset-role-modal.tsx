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
import { DatasetRoleOption, PermissionOption } from "@/lib/types.ts";
import { PermissionChecklist } from "@/components/roles/permission-checklist.tsx";

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
  const [open, setOpen] = useState(false);
  const [permissionOptions, setPermissionOptions] = useState<PermissionOption[]>([]);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([]);

  const form = useForm<DatasetRoleFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: role?.name ?? ""
    }
  });

  useEffect(() => {
    if (!open) return;
    api.permissions().getPermissions("dataset").then(setPermissionOptions);
    if (role) {
      api.datasetRoles().getDatasetRoleDetail(role.id).then((detail) => {
        form.reset({ name: detail.name });
        setSelectedPermissionIds(detail.permissionIds);
      });
    } else {
      form.reset({ name: "" });
      setSelectedPermissionIds([]);
    }
  }, [open, role, form]);

  const handleSubmit = async (values: DatasetRoleFormSchema) => {
    if (role) {
      await api.datasetRoles().updateDatasetRole(role.id, values.name, selectedPermissionIds);
    } else {
      await api.datasetRoles().createDatasetRole(values.name, selectedPermissionIds);
    }
    setOpen(false);
    onSaved();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={role ? "secondary" : "default"}>{role ? "Edit" : "New Role"}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{role ? `Edit ${role.name}` : "New Dataset Role"}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
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
            <PermissionChecklist
              options={permissionOptions}
              selectedIds={selectedPermissionIds}
              onChange={setSelectedPermissionIds}
            />
            <Button type="submit">Save</Button>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
