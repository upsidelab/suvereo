import { FormControl, FormDescription, FormField, FormItem, FormLabel } from "@/components/ui/form.tsx";
import { Switch } from "@/components/ui/switch.tsx";
import { UseFormReturn } from "react-hook-form";
import { useEffect, useState } from "react";
import { ApiClient } from "@/lib/api.ts";
import { GroupOption } from "@/lib/types.ts";
import { GroupSelectionFields } from "@/components/util/group-selection-fields.tsx";

const api = new ApiClient();

export interface PermissionFieldsProps {
  form: UseFormReturn<any, any, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export function PermissionFields({ form }: PermissionFieldsProps) {
  const [groups, setGroups] = useState<GroupOption[]>([]);

  useEffect(() => {
    api.groups().getGroups().then(setGroups);
  }, []);

  return (
    <>
      <h3 className="mb-4 text-lg font-medium">Permissions</h3>
      <FormField
        control={form.control}
        name="isActive"
        render={({field}) => (
          <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <FormLabel className="text-base">
                Active
              </FormLabel>
              <FormDescription>
                Controls whether the user is able to sign in.
              </FormDescription>
            </div>
            <FormControl>
              <Switch
                checked={field.value}
                onCheckedChange={field.onChange}
              />
            </FormControl>
          </FormItem>
        )}
      />
      <GroupSelectionFields form={form} groups={groups} />
    </>
  )
}
