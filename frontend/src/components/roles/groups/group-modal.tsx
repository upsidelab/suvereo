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
import { GroupOption } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { GroupMembersPanel } from "@/components/roles/groups/group-members-panel.tsx";
import { GroupGlobalRolesPanel } from "@/components/roles/groups/group-global-roles-panel.tsx";
import { GroupDataSetRolesPanel } from "@/components/roles/groups/group-data-set-roles-panel.tsx";
import { ModalSection, ModalSections } from "@/components/roles/modal-sections.tsx";
import { ModalScrollArea } from "@/components/roles/modal-scroll-area.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
  description: z.string().trim(),
});
type GroupFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

type Section = "details" | "members" | "global-roles" | "data-set-roles";

const SECTIONS: readonly ModalSection<Section>[] = [
  { key: "details", label: "Details" },
  { key: "members", label: "Members" },
  { key: "global-roles", label: "Global Roles" },
  { key: "data-set-roles", label: "Data Set Roles" },
];

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
    defaultValues: { name: group?.name ?? "", description: group?.description ?? "" }
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSection("details");
    setMemberCount(group?.memberCount ?? 0);
    form.reset({ name: group?.name ?? "", description: group?.description ?? "" });
  }, [open, group, form]);

  // The list behind the dialog is refreshed on close, not here: a fresh `group` object would
  // send the effect above back to the Details section.
  const refreshCounts = async () => {
    if (group?.id == null) return;
    setMembershipChanged(true);
    try {
      setMemberCount((await api.groups().getGroupDetail(group.id)).memberCount);
    } catch {
      // The panel reports its own failure; a stale count is not worth a second message.
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
      ? await api.groups().updateGroup(group.id, values.name, values.description)
      : await api.groups().createGroup(values.name, values.description);

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      if (Array.isArray(body.name)) {
        form.setError("name", { message: body.name[0] });
      } else if (Array.isArray(body.description)) {
        form.setError("description", { message: body.description[0] });
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
        <ModalSections sections={SECTIONS} active={section} onChange={setSection} />

        {/* Fixed height, so switching sections cannot resize the dialog. */}
        <div className="h-[min(62vh,34rem)] flex flex-col">
          {section === "details" && (
            <Form {...form}>
              <form onSubmit={form.handleSubmit(save)} className="flex grow flex-col space-y-4 min-h-0">
                <ModalScrollArea className="flex flex-col space-y-4">
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
                  <p className="text-sm text-muted-foreground">
                    A group holds people, not permissions. It reaches its members through the global roles granted
                    to it and the data set roles it is granted on individual data sets.
                  </p>
                  {!canEdit && (
                    <p className="text-sm text-muted-foreground">You can't edit this group's details.</p>
                  )}
                </ModalScrollArea>
                {canEdit && (
                  <div className="flex justify-end">
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

          {section === "data-set-roles" && (
            group?.id != null
              ? <GroupDataSetRolesPanel groupId={group.id} memberCount={memberCount} onChanged={refreshCounts} />
              : <p className="text-sm text-muted-foreground">Save the group first to grant it roles.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
