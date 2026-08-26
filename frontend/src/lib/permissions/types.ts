export type PermissionOption = {
  code: string;
  label: string;
  requires: string[];
};


export type MissingPermission = {
  code: string;
  required_by: string[];
};

export type PermissionEntity = {
  entity: string;
  label: string;
  permissions: PermissionOption[];
};
