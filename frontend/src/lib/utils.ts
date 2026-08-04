import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Display-only: capitalizes a role/group name for consistent presentation ("Admin", "Viewer",
// "Editor") without touching the underlying stored name, which several call sites still match
// on exactly (e.g. the dataset role picker submits the raw, lowercase name).
export function capitalize(text: string): string {
  return text.length === 0 ? text : text.charAt(0).toUpperCase() + text.slice(1);
}
