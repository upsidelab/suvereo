import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface NewGroupModalProps {
  onGroupCreated: () => void;
}

export function NewGroupModal({ onGroupCreated }: NewGroupModalProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  const handleSubmit = async () => {
    await api.groups().createGroup(name);
    setName("");
    setOpen(false);
    onGroupCreated();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="default">New Group</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Group</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Input placeholder="Group name" value={name} onChange={(e) => setName(e.target.value)} />
          <Button onClick={handleSubmit} disabled={!name.trim()}>Create</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
