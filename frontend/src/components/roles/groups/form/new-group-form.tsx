import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form.tsx";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";

const formSchema = z.object({
  name: z.string().trim().min(1),
});
type NewGroupFormSchema = z.infer<typeof formSchema>;

const api = new ApiClient(authenticationProviderInstance);

export interface NewGroupFormProps {
  onGroupCreated: () => void;
}

export function NewGroupForm({ onGroupCreated }: NewGroupFormProps) {
  const form = useForm<NewGroupFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: ""
    }
  });

  const handleSubmit = async (values: NewGroupFormSchema) => {
    await api.groups().createGroup(values.name);
    form.reset();
    onGroupCreated();
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Group name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Create</Button>
      </form>
    </Form>
  );
}
