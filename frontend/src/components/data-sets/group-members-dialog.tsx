import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { GroupMember } from "@/lib/types.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface GroupMembersDialogProps {
  groupId: number | null;
  groupName: string;
  onClose: () => void;
}

export function GroupMembersDialog({ groupId, groupName, onClose }: GroupMembersDialogProps) {
  const [members, setMembers] = useState<GroupMember[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (groupId === null) return;
    setMembers(null);
    setError(null);
    api.groups().getGroupMembers(groupId)
      .then(setMembers)
      .catch(() => setError("Could not load this group's members."));
  }, [groupId]);

  return (
    <Dialog open={groupId !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="w-[min(92vw,28rem)] max-w-none">
        <DialogHeader>
          <DialogTitle>Members of {groupName}</DialogTitle>
        </DialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <ScrollArea className="h-[18rem] w-full rounded-md border px-4 py-2">
          {members === null && !error && <p className="text-sm text-muted-foreground">Loading...</p>}
          {members?.length === 0 && (
            <p className="text-sm text-muted-foreground">
              This group has no members, so granting it a role reaches nobody yet.
            </p>
          )}
          {members?.map((member) => (
            <p key={member.id} className="text-sm py-1">
              {member.email}{member.isServiceAccount && " (service account)"}
            </p>
          ))}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
