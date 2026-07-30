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
import { GroupOption, PermissionOption } from "@/lib/types.ts";
import { PermissionChecklist } from "@/components/roles/permission-checklist.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type GlobalRoleFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

export interface GlobalRoleModalProps {
  group?: GroupOption;
  onSaved: () => void;
}

export function GlobalRoleModal({ group, onSaved }: GlobalRoleModalProps) {
  const [open, setOpen] = useState(false);
  const [permissionOptions, setPermissionOptions] = useState<PermissionOption[]>([]);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<GlobalRoleFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: group?.name ?? ""
    }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    api.permissions().getPermissions("global").then(setPermissionOptions);
    if (group) {
      api.groups().getGroupDetail(group.id).then((detail) => {
        form.reset({ name: detail.name });
        setSelectedPermissionIds(detail.permissionIds);
      });
    } else {
      form.reset({ name: "" });
      setSelectedPermissionIds([]);
    }
  }, [open, group, form]);

  const handleSubmit = async (values: GlobalRoleFormSchema) => {
    setError(null);
    const response = group
      ? await api.groups().updateGroup(group.id, values.name, selectedPermissionIds)
      : await api.groups().createGroup(values.name, selectedPermissionIds);
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
        <Button variant={group ? "secondary" : "default"}>{group ? "Edit" : "New Role"}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{group ? `Edit ${group.name}` : "New Global Role"}</DialogTitle>
        </DialogHeader>
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
