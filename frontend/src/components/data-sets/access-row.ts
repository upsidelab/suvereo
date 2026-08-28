import { DataSetRoleOption } from "@/lib/types.ts";

export type AccessSubject = {
  type: "user" | "group";
  id: number;
  label: string;
  memberCount?: number;
};

export type AccessRow = {
  subject: AccessSubject;
  role: DataSetRoleOption;
};
