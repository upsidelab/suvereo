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
import { GroupOption } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { GroupMembersPanel } from "@/components/roles/groups/group-members-panel.tsx";
import { GroupGlobalRolesPanel } from "@/components/roles/groups/group-global-roles-panel.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type GroupFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

type Section = "details" | "members" | "global-roles";

export interface GroupModalProps {
  group?: GroupOption;
  onSaved: () => void;
}

export function GroupModal({ group, onSaved }: GroupModalProps) {
  const { hasPermission } = useApplicationContext()!;
  const canEdit = group ? hasPermission(PERMISSIONS.GROUP.CHANGE) : hasPermission(PERMISSIONS.GROUP.ADD);

  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<Section>("details");
  const [memberCount, setMemberCount] = useState(group?.memberCount ?? 0);
  const [membershipChanged, setMembershipChanged] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<GroupFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: group?.name ?? "" }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSection("details");
    setMemberCount(group?.memberCount ?? 0);
    form.reset({ name: group?.name ?? "" });
  }, [open, group, form]);

  // The panels change what the counts would say, and the count is the whole point of showing it
  // next to a control that hands out access - so re-read it rather than let it go stale. The list
  // behind the dialog is refreshed on close instead of now: reloading it here would hand this
  // component a new `group` object and send the effect above back to the Details section.
  const refreshCounts = async () => {
    if (group?.id == null) return;
    setMembershipChanged(true);
    try {
      setMemberCount((await api.groups().getGroupDetail(group.id)).memberCount);
    } catch {
      // The panel that just changed something reports its own failure; a stale count is not
      // worth a second error message.
    }
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next && membershipChanged) {
      setMembershipChanged(false);
      onSaved();
    }
  };

  const save = async (values: GroupFormSchema) => {
    setError(null);
    const response = group?.id != null
      ? await api.groups().updateGroup(group.id, values.name)
      : await api.groups().createGroup(values.name);

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      if (Array.isArray(body.name)) {
        form.setError("name", { message: body.name[0] });
      } else {
        setError(body.detail ?? "Could not save this group.");
      }
      return;
    }

    setOpen(false);
    onSaved();
  };

  const triggerLabel = group ? (canEdit ? "Edit" : "View") : "New group";
  const title = group ? (canEdit ? `Edit group ${group.name}` : `Group ${group.name}`) : "New group";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant={group ? "secondary" : "default"}>{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent className="w-[min(92vw,36rem)] max-w-none">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {error && <p className="text-sm text-destructive mb-4">{error}</p>}
        <div className="flex items-center space-x-2 border-b pb-2 mb-4">
          <Button type="button" variant={section === "details" ? "default" : "ghost"} onClick={() => setSection("details")}>
            Details
          </Button>
          <Button type="button" variant={section === "members" ? "default" : "ghost"} onClick={() => setSection("members")}>
            Members
          </Button>
          <Button
            type="button"
            variant={section === "global-roles" ? "default" : "ghost"}
            onClick={() => setSection("global-roles")}
          >
            Global Roles
          </Button>
        </div>

        {/* All three sections share a fixed height, so switching between them cannot resize the dialog. */}
        <div className="h-[26rem] flex flex-col">
          {section === "details" && (
            <Form {...form}>
              <form onSubmit={form.handleSubmit(save)} className="flex grow flex-col space-y-4 min-h-0">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Group name" disabled={!canEdit} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <p className="text-sm text-muted-foreground">
                  A group holds people, not permissions. It reaches its members through the global roles granted
                  to it and the dataset roles it is granted on individual data sets.
                </p>
                {!canEdit && <p className="text-sm text-muted-foreground">You can't rename this group.</p>}
                {canEdit && (
                  <div className="flex grow items-end justify-end">
                    <Button type="submit">Save</Button>
                  </div>
                )}
              </form>
            </Form>
          )}

          {section === "members" && (
            group?.id != null
              ? <GroupMembersPanel groupId={group.id} onChanged={refreshCounts} />
              : <p className="text-sm text-muted-foreground">Save the group first to add members.</p>
          )}

          {section === "global-roles" && (
            group?.id != null
              ? <GroupGlobalRolesPanel groupId={group.id} memberCount={memberCount} onChanged={refreshCounts} />
              : <p className="text-sm text-muted-foreground">Save the group first to grant it roles.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
