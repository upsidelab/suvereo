import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form.tsx";
import { ApiClient } from "@/lib/api.ts";
import { DatasetRoleOption, PermissionOption } from "@/lib/types.ts";
import { PermissionChecklist } from "@/components/roles/permission-checklist.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type DatasetRoleFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient();

export interface DatasetRoleModalProps {
  role?: DatasetRoleOption;
  onSaved: () => void;
}

export function DatasetRoleModal({ role, onSaved }: DatasetRoleModalProps) {
  const [open, setOpen] = useState(false);
  const [permissionOptions, setPermissionOptions] = useState<PermissionOption[]>([]);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<DatasetRoleFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: role?.name ?? ""
    }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
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
    setError(null);
    const response = role
      ? await api.datasetRoles().updateDatasetRole(role.id, values.name, selectedPermissionIds)
      : await api.datasetRoles().createDatasetRole(values.name, selectedPermissionIds);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? "Could not save this role.");
      return;
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
          <DialogTitle>{role ? `Edit role ${role.name}` : "New Dataset Role"}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground -mt-2 mb-2">
          This only defines the role. To grant it to a user or group, go to Data Sets → Manage Access for that data set.
        </p>
        {error && <p className="text-sm text-destructive mb-4">{error}</p>}
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
