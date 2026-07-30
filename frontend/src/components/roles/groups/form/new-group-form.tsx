import { useState } from "react";
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
  const [error, setError] = useState<string | null>(null);
  const form = useForm<NewGroupFormSchema>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: ""
    }
  });

  const handleSubmit = async (values: NewGroupFormSchema) => {
    setError(null);
    const response = await api.groups().createGroup(values.name);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? "Could not create this group.");
      return;
    }
    form.reset();
    onGroupCreated();
  };

  return (
    <Form {...form}>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
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
