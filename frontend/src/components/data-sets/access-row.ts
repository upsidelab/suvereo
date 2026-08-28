import { DatasetRoleOption } from "@/lib/types.ts";

export type AccessSubject = {
  type: "user" | "global-role";
  id: number;
  label: string;
};

export type AccessRow = {
  subject: AccessSubject;
  role: DatasetRoleOption;
};
