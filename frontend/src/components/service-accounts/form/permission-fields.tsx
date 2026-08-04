import { useEffect, useState } from "react";
import { FormControl, FormDescription, FormField, FormItem, FormLabel } from "@/components/ui/form.tsx";
import { Switch } from "@/components/ui/switch.tsx";
import { UseFormReturn, useWatch } from "react-hook-form";
import { PermissionOption } from "@/lib/types.ts";
import { PermissionChecklist } from "@/components/roles/permission-checklist.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface PermissionFieldsProps {
  form: UseFormReturn<any, any, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export function PermissionFields({ form }: PermissionFieldsProps) {
  const [permissionOptions, setPermissionOptions] = useState<PermissionOption[]>([]);
  const isAdmin = useWatch({ control: form.control, name: "isAdmin" }) as boolean;

  useEffect(() => {
    api.permissions().getPermissions("dataset").then(setPermissionOptions);
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
                Controls whether the service account is able to use the API.
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
      <FormField
        control={form.control}
        name="isAdmin"
        render={({field}) => (
          <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <FormLabel className="text-base">
                Admin
              </FormLabel>
              <FormDescription>
                Admins can manage data sets and users.
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
      {!isAdmin &&
        <FormItem>
          <div className="mb-2">
            <h3 className="text-base font-medium">Dataset Permissions</h3>
            <FormDescription>
              Select exactly what this account can do. These permissions apply to every data set selected below --
              nothing is granted anywhere else.
            </FormDescription>
          </div>
          <FormField
            control={form.control}
            name="permissionIds"
            render={({ field }) => (
              <FormControl>
                <PermissionChecklist
                  options={permissionOptions}
                  selectedIds={field.value as number[]}
                  onChange={field.onChange}
                />
              </FormControl>
            )}
          />
        </FormItem>
      }
    </>
  )
}
