import { useState } from "react";
import { Form } from "@/components/ui/form.tsx";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { Button } from "@/components/ui/button.tsx";
import { PasswordFields } from "@/components/users/form/password-fields.tsx";
import { AccountAccessFields } from "@/components/users/form/account-access-fields.tsx";
import { DetailsFields } from "@/components/users/form/details-fields.tsx";

const formSchema = z.object({
  email: z.string().trim().email(),
  password: z.string().min(8),
  confirmPassword: z.string(),
  isActive: z.boolean(),
  isAdmin: z.boolean(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
});

type UserFormSchema = z.infer<typeof formSchema>;
const api = new ApiClient(authenticationProviderInstance);

export interface NewUserFormProps {
  onUserCreated: () => void;
}

export function NewUserForm({ onUserCreated }: NewUserFormProps) {
  const [error, setError] = useState<string | null>(null);
  const form = useForm<UserFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
      isActive: true,
      isAdmin: false
    }
  });

  const handleSubmit = async (values: UserFormSchema) => {
    setError(null);
    const response = await api.users().createUser(values);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not create this user.");
      return;
    }
    onUserCreated();
    form.reset();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DetailsFields form={form} />
        <PasswordFields form={form} />
        <AccountAccessFields form={form} />
        <Button type="submit">Create</Button>
      </form>
    </Form>
  )
}
