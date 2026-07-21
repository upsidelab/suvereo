import { useEffect, useState } from "react";
import { Form } from "@/components/ui/form.tsx";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button.tsx";
import { checkServiceNameAvailability } from "@/components/util/check-service-name-availability.tsx";
import { DetailsFields } from "@/components/service-accounts/form/details-fields.tsx";
import { ApiClient } from "@/lib/api.ts";
import { ServiceAccount, GroupOption } from "@/lib/types.ts";
import { PermissionFields } from "@/components/service-accounts/form/permission-fields.tsx";

const api = new ApiClient();

const formSchema = z.object({
  oldName: z.string().trim(),
  name: z.string().trim().min(1),
  isActive: z.boolean(),
  groupIds: z.array(z.number()),
}).refine(async (data) => data.name === data.oldName || await checkServiceNameAvailability(data.name), {
  message: "The name has already been taken",
  path: ["name"],
});

type CreateServiceAccountFormSchema = z.infer<typeof formSchema>;

export interface EditServiceAccountFormProps {
  serviceAccount: ServiceAccount;
  onServiceAccountUpdated: () => void;
}

export function EditServiceAccountForm({ serviceAccount, onServiceAccountUpdated }: EditServiceAccountFormProps) {
  const [error, setError] = useState<string | null>(null);
  const oldName = serviceAccount.email.split('@')[0];
  const form = useForm<CreateServiceAccountFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: oldName,
      oldName: oldName,
      isActive: serviceAccount.isActive,
      groupIds: serviceAccount.groupIds || [],
    }
  });
  const [groups, setGroups] = useState<GroupOption[]>([]);

  useEffect(() => {
    api.groups().getGroups().then(setGroups);
  }, []);

  const handleSubmit = async (values: CreateServiceAccountFormSchema) => {
    setError(null);
    const response = await api.serviceAccounts().updateServiceAccount(serviceAccount.id, values);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? body.group_ids?.[0] ?? "Could not update this service account.");
      return;
    }
    onServiceAccountUpdated();
  };

  return (
    <>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DetailsFields form={form}/>
          <PermissionFields form={form} groups={groups}/>
          <Button type="submit">Update</Button>
        </form>
      </Form>
    </>
  );
}
