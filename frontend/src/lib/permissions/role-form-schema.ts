import { z } from "zod";

export const GLOBAL_ROLE_NAME_MAX_LENGTH = 150;
export const DATA_SET_ROLE_NAME_MAX_LENGTH = 100;

export function roleFormSchema(maxNameLength: number, takenNames: readonly string[]) {
  return z.object({
    name: z.string().trim().min(1)
      .max(maxNameLength, `Ensure this field has no more than ${maxNameLength} characters.`)
      .refine((name) => !takenNames.includes(name), "A role with this name already exists."),
    description: z.string().trim(),
  });
}

export type RoleFormSchema = z.infer<ReturnType<typeof roleFormSchema>>;
