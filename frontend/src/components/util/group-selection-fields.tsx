import { FormControl, FormDescription, FormField, FormItem, FormLabel } from "@/components/ui/form.tsx";
import { Switch } from "@/components/ui/switch.tsx";
import { UseFormReturn, useWatch } from "react-hook-form";
import { GroupOption } from "@/lib/types.ts";
import { CheckboxListInput } from "@/components/util/checkbox-list-input.tsx";

const ADMIN_GROUP_NAME = "Admin";

export interface GroupSelectionFieldsProps {
  form: UseFormReturn<any, any, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  groups: GroupOption[];
}

export function GroupSelectionFields({ form, groups }: GroupSelectionFieldsProps) {
  const adminGroup = groups.find((g) => g.name === ADMIN_GROUP_NAME);
  const otherGroups = groups.filter((g) => g.name !== ADMIN_GROUP_NAME);
  const groupIds = useWatch({ control: form.control, name: "groupIds" }) as number[];

  const handleAdminToggle = (checked: boolean) => {
    if (!adminGroup) return;
    const next = checked
      ? [...groupIds, adminGroup.id]
      : groupIds.filter((id) => id !== adminGroup.id);
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
          <Switch
            checked={adminGroup ? groupIds.includes(adminGroup.id) : false}
            onCheckedChange={handleAdminToggle}
          />
        </FormControl>
      </FormItem>
      {otherGroups.length > 0 &&
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
                  options={otherGroups.map((group) => ({ id: group.id, label: group.name }))}
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
