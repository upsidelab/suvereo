import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button.tsx";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GroupMember } from "@/lib/types.ts";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { RevokeOwnAdminAccessDialog } from "@/components/roles/revoke-own-admin-access-dialog.tsx";

const api = new ApiClient(authenticationProviderInstance);

export function AdminMembersPanel() {
  const { account, setAccount } = useApplicationContext()!;
  const canWrite = !!account?.isAdmin;
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [candidates, setCandidates] = useState<GroupMember[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string>("");
  const [isSelfDemotionDialogOpen, setIsSelfDemotionDialogOpen] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    let admins: GroupMember[];
    try {
      admins = await api.getAdmins();
    } catch {
      setMembers([]);
      setListError("You don't have access to the list of admins.");
      return;
    }
    setMembers(admins);
    setListError(null);

    if (!canWrite) return;
    try {
      const [users, serviceAccounts] = await Promise.all([
        api.getAllUsers(),
        api.serviceAccounts().getAllServiceAccounts(),
      ]);
      const adminIds = new Set(admins.map((admin) => admin.id));
      setCandidates([
        ...users.map((user) => ({ id: user.id, email: user.email, isServiceAccount: false })),
        ...serviceAccounts.map((account) => ({ id: account.id, email: account.email, isServiceAccount: true })),
      ].filter((candidate) => !adminIds.has(candidate.id)));
    } catch {
      setCandidates([]);
    }
  }, [canWrite]);

  useEffect(() => {
    load();
  }, [load]);

  const setAdmin = async (subject: GroupMember, isAdmin: boolean) => {
    const response = subject.isServiceAccount
      ? await api.serviceAccounts().setServiceAccountAdmin(subject.id, isAdmin)
      : await api.users().setUserAdmin(subject.id, isAdmin);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail ?? "Could not change admin access for this account.");
      return;
    }
    if (subject.email === account?.email) {
      setAccount(await api.getAccount());
    }
    await load();
  };

  const handleAdd = async () => {
    const subject = candidates.find((candidate) => subjectKey(candidate) === selectedSubject);
    if (!subject) return;
    setSelectedSubject("");
    await setAdmin(subject, true);
  };

  const handleRemove = async (subject: GroupMember) => {
    if (subject.email === account?.email) {
      setIsSelfDemotionDialogOpen(true);
      return;
    }
    await setAdmin(subject, false);
  };

  const confirmSelfDemotion = async () => {
    setIsSelfDemotionDialogOpen(false);
    const self = members.find((member) => member.email === account?.email);
    if (self) await setAdmin(self, false);
  };

  return (
    <div className="flex flex-col grow min-h-0">
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {listError && <p className="text-sm text-muted-foreground mb-4">{listError}</p>}
      {canWrite && (
        <div className="flex space-x-4 mb-4">
          <Select value={selectedSubject} onValueChange={setSelectedSubject}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Select a user..." />
            </SelectTrigger>
            <SelectContent>
              {candidates.map((candidate) => (
                <SelectItem key={subjectKey(candidate)} value={subjectKey(candidate)}>
                  {candidate.email}{candidate.isServiceAccount && " (service account)"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleAdd} disabled={!selectedSubject}>Add</Button>
        </div>
      )}
      <ScrollArea className="grow min-h-0 w-full rounded-md border px-4 py-2">
        {members.length === 0
          ? !listError && <p className="text-sm text-muted-foreground">No admins yet.</p>
          : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-full">Email</TableHead>
                  {canWrite && <TableHead className="whitespace-nowrap">Action</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((member) => (
                  <TableRow key={subjectKey(member)}>
                    <TableCell width="100%">{member.email}{member.isServiceAccount && " (service account)"}</TableCell>
                    {canWrite && (
                      <TableCell className="whitespace-nowrap">
                        <Button variant="secondary" onClick={() => handleRemove(member)}>Remove</Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
      </ScrollArea>

      <RevokeOwnAdminAccessDialog
        open={isSelfDemotionDialogOpen}
        onConfirm={confirmSelfDemotion}
        onCancel={() => setIsSelfDemotionDialogOpen(false)}
      />
    </div>
  );
}

function subjectKey(subject: GroupMember): string {
  return `${subject.isServiceAccount ? "service-account" : "user"}:${subject.id}`;
}
