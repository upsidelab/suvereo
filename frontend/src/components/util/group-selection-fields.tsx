import { useEffect } from "react";
import { FormControl, FormDescription, FormField, FormItem, FormLabel } from "@/components/ui/form.tsx";
import { Switch } from "@/components/ui/switch.tsx";
import { UseFormReturn, useWatch } from "react-hook-form";
import { GroupOption } from "@/lib/types.ts";
import { CheckboxListInput } from "@/components/util/checkbox-list-input.tsx";
import { capitalize } from "@/lib/utils.ts";

const ADMIN_GROUP_NAME = "Admin";

export interface GroupSelectionFieldsProps {
  form: UseFormReturn<any, any, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  groups: GroupOption[];
}

export function GroupSelectionFields({ form, groups }: GroupSelectionFieldsProps) {
  const adminGroup = groups.find((g) => g.name === ADMIN_GROUP_NAME);
  const otherGroups = groups.filter((g) => g.name !== ADMIN_GROUP_NAME);
  const groupIds = useWatch({ control: form.control, name: "groupIds" }) as number[];
  const isAdmin = adminGroup ? groupIds.includes(adminGroup.id) : false;

  // Admin is the highest privilege level: holding any other role alongside it is
  // meaningless (Admin already implies everything a lesser role could grant), so
  // additional roles are hidden and cleared once Admin is on — mirrors how the
  // service account form hides/clears its Data Sets picker for the same reason.
  useEffect(() => {
    if (isAdmin && adminGroup && groupIds.length > 1) {
      form.setValue("groupIds", [adminGroup.id]);
    }
  }, [isAdmin, adminGroup, groupIds, form]);

  const handleAdminToggle = (checked: boolean) => {
    if (!adminGroup) return;
    const next = checked ? [adminGroup.id] : groupIds.filter((id) => id !== adminGroup.id);
    form.setValue("groupIds", next);
  };

  return (
    <>
      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
        <div className="space-y-0.5">
          <FormLabel className="text-base">Admin</FormLabel>
          <FormDescription>Admins can manage data sets and users.</FormDescription>
        </div>
        <FormControl>
          <Switch checked={isAdmin} onCheckedChange={handleAdminToggle} />
        </FormControl>
      </FormItem>
      {!isAdmin && otherGroups.length > 0 &&
        <FormItem>
          <div className="mb-2">
            <h3 className="text-base font-medium">Additional Roles</h3>
            <FormDescription>Select any other global roles this account should hold.</FormDescription>
          </div>
          <FormField
            control={form.control}
            name="groupIds"
            render={({ field }) => (
              <FormControl>
                <CheckboxListInput
                  options={otherGroups.map((group) => ({ id: group.id, label: capitalize(group.name) }))}
                  selectedIds={field.value as number[]}
                  onChange={field.onChange}
                />
              </FormControl>
            )}
          />
        </FormItem>
      }
    </>
  );
}
