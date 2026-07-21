import { ApiClient } from "@/lib/api.ts";

const api = new ApiClient();

export async function checkServiceNameAvailability(name: string): Promise<boolean> {
  const response = await api.serviceAccounts().checkServiceNameAvailability(name);
  return response;
}