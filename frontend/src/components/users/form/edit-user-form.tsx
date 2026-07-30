import { useState } from "react";
import { Form } from "@/components/ui/form.tsx";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { Button } from "@/components/ui/button.tsx";
import { PermissionFields } from "@/components/users/form/permission-fields.tsx";
import { DetailsFields } from "@/components/users/form/details-fields.tsx";
import { User } from "@/lib/types.ts";

const formSchema = z.object({
  email: z.string().trim().email(),
  isActive: z.boolean(),
  groupIds: z.array(z.number()),
});

type UserFormSchema = z.infer<typeof formSchema>;
const api = new ApiClient(authenticationProviderInstance);

export interface EditUserFormProps {
  user: User;
  onUserUpdated: () => void;
}

export function EditUserForm({ user, onUserUpdated }: EditUserFormProps) {
  const [error, setError] = useState<string | null>(null);
  const form = useForm<UserFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: user.email,
      isActive: user.isActive,
      groupIds: user.groupIds
    }
  });

  const handleSubmit = async (values: UserFormSchema) => {
    setError(null);
    const response = await api.users().updateUser(user.id, values);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? body.group_ids?.[0] ?? "Could not update this user.");
      return;
    }
    onUserUpdated();
    form.reset();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DetailsFields form={form} />
        <PermissionFields form={form} />
        <Button type="submit">Update</Button>
      </form>
    </Form>
  )
}
