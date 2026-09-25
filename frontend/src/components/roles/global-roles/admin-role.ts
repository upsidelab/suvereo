export type GlobalRole = {
  id: number | null;
  name: string;
  description?: string;
  isBuiltIn?: boolean;
};

export const ADMIN_ROLE: GlobalRole = {
  id: null,
  name: "Admin",
  description: "Full access to everything, including making other people admins. Cannot be edited.",
  isBuiltIn: true,
};

export function isAdminRole(role?: GlobalRole): boolean {
  return role?.id === null;
}
