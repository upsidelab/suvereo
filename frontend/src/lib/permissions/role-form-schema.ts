import { z } from "zod";

export const ROLE_NAME_MAX_LENGTH = 150;

export function roleFormSchema(takenNames: readonly string[]) {
  return z.object({
    name: z.string().trim().min(1)
      .max(ROLE_NAME_MAX_LENGTH, `Ensure this field has no more than ${ROLE_NAME_MAX_LENGTH} characters.`)
      .refine((name) => !takenNames.includes(name), "A role with this name already exists."),
    description: z.string().trim(),
  });
}

export type RoleFormSchema = z.infer<ReturnType<typeof roleFormSchema>>;
