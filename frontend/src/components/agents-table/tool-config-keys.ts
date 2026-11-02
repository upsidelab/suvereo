export const TOOLS_SECTION = "tools";

export function toolFieldKey(toolName: string, field: string): string {
  return `${TOOLS_SECTION}.${toolName}.${field}`;
}

export function isToolFieldKey(key: string): boolean {
  return key.startsWith(`${TOOLS_SECTION}.`);
}
