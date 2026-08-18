import { DatasetRoleOption } from "@/lib/types.ts";

export type AccessSubject = {
  type: "user" | "group";
  id: number;
  label: string;
};

export type AccessRow = {
  subject: AccessSubject;
  role: DatasetRoleOption;
};
