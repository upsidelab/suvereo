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
import { RevokeOwnAdminAccessDialog } from "@/components/roles/revoke-own-admin-access-dialog.tsx";
import { User } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";

const formSchema = z.object({
  email: z.string().trim().email(),
  isActive: z.boolean(),
  isAdmin: z.boolean(),
});

type UserFormSchema = z.infer<typeof formSchema>;
const api = new ApiClient(authenticationProviderInstance);

export interface EditUserFormProps {
  user: User;
  onUserUpdated: () => void;
}

export function EditUserForm({ user, onUserUpdated }: EditUserFormProps) {
  const { account, setAccount } = useApplicationContext()!;
  const isOwnAccount = account?.email === user.email;
  const [valuesAwaitingConfirmation, setValuesAwaitingConfirmation] = useState<UserFormSchema | null>(null);

  const form = useForm<UserFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: user.email,
      isActive: user.isActive,
      isAdmin: user.isAdmin
    }
  });

  const update = async (values: UserFormSchema) => {
    await api.users().updateUser(user.id, values);
    if (isOwnAccount) {
      setAccount(await api.getAccount());
    }
    onUserUpdated();
    form.reset();
  }

  const handleSubmit = async (values: UserFormSchema) => {
    const revokesOwnAdminAccess = isOwnAccount && user.isAdmin && !values.isAdmin;
    if (revokesOwnAdminAccess) {
      setValuesAwaitingConfirmation(values);
      return;
    }
    await update(values);
  }

  const confirmRevokingOwnAdminAccess = async () => {
    const values = valuesAwaitingConfirmation;
    setValuesAwaitingConfirmation(null);
    if (values) {
      await update(values);
    }
  }

  return (
    <>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          <DetailsFields form={form} />
          <PermissionFields form={form} />
          <Button type="submit">Update</Button>
        </form>
      </Form>
      <RevokeOwnAdminAccessDialog
        open={valuesAwaitingConfirmation !== null}
        onConfirm={confirmRevokingOwnAdminAccess}
        onCancel={() => setValuesAwaitingConfirmation(null)}
      />
    </>
  )
}
