export type GlobalRole = {
  id: number | null;
  name: string;
  isBuiltIn?: boolean;
};

export const ADMIN_ROLE: GlobalRole = { id: null, name: "Admin", isBuiltIn: true };

export function isAdminRole(role?: GlobalRole): boolean {
  return role?.id === null;
}
