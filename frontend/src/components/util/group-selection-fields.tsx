import { FormControl, FormDescription, FormField, FormItem, FormLabel } from "@/components/ui/form.tsx";
import { Switch } from "@/components/ui/switch.tsx";
import { Checkbox } from "@/components/ui/checkbox.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import { UseFormReturn, useWatch } from "react-hook-form";
import { GroupOption } from "@/lib/types.ts";

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
          <ScrollArea className="h-[200px] w-full rounded-md border px-4 py-2">
            <div className="space-y-2">
              {otherGroups.map((group) => (
                <FormField
                  key={group.id}
                  name="groupIds"
                  control={form.control}
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center space-x-3 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={(field.value as number[]).includes(group.id)}
                          onCheckedChange={(checked) => {
                            const next = checked
                              ? [...(field.value as number[]), group.id]
                              : (field.value as number[]).filter((id: number) => id !== group.id);
                            field.onChange(next);
                          }}
                        />
                      </FormControl>
                      <FormLabel className="text-sm font-normal">{group.name}</FormLabel>
                    </FormItem>
                  )}
                />
              ))}
            </div>
          </ScrollArea>
        </FormItem>
      }
    </>
  );
}
