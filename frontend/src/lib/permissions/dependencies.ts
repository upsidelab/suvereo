import { MissingPermission, PermissionEntity } from "@/lib/permissions/types.ts";


export function missingDependencies(selected: string[], entities: PermissionEntity[]): MissingPermission[] {
  const granted = new Set(selected);
  const requiredBy = new Map<string, string[]>();

  for (const entity of entities) {
    for (const option of entity.permissions) {
      if (!granted.has(option.code)) continue;
      for (const required of option.requires) {
        if (granted.has(required)) continue;
        requiredBy.set(required, [...(requiredBy.get(required) ?? []), option.code]);
      }
    }
  }

  return [...requiredBy.entries()]
    .map(([code, dependents]) => ({ code, required_by: [...dependents].sort() }))
    .sort((first, second) => first.code.localeCompare(second.code));
}

export function unresolvedRequirements(missing: MissingPermission[], selected: string[]): MissingPermission[] {
  const granted = new Set(selected);
  const unresolved = missing.filter(
    (entry) => !granted.has(entry.code) && entry.required_by.some((code) => granted.has(code)),
  );

  return unresolved.length === missing.length ? missing : unresolved;
}
