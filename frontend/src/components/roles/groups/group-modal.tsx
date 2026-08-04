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
import { GroupMembersPanel } from "@/components/roles/groups/group-members-panel.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type GroupFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

type Section = "permissions" | "members";

export interface GroupModalProps {
  group?: GroupOption;
  onSaved: () => void;
}

export function GroupModal({ group, onSaved }: GroupModalProps) {
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<Section>("permissions");
  const [permissionOptions, setPermissionOptions] = useState<PermissionOption[]>([]);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<GroupFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: group?.name ?? ""
    }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSection("permissions");
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

  const handleSubmit = async (values: GroupFormSchema) => {
    setError(null);
    const response = group
      ? await api.groups().updateGroup(group.id, values.name, selectedPermissionIds)
      : await api.groups().createGroup(values.name, selectedPermissionIds);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? "Could not save this group.");
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
          <DialogTitle>{group ? `Edit role ${group.name}` : "New Role"}</DialogTitle>
        </DialogHeader>
        {error && <p className="text-sm text-destructive mb-4">{error}</p>}
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
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Group name" {...field} />
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
        )}
        {section === "members" && (
          group
            ? <GroupMembersPanel groupId={group.id} />
            : <p className="text-sm text-muted-foreground">Save the group first to add members.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
