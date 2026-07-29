import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { NewGroupForm } from "@/components/roles/groups/form/new-group-form.tsx";

export interface NewGroupModalProps {
  onGroupCreated: () => void;
}

export function NewGroupModal({ onGroupCreated }: NewGroupModalProps) {
  const [open, setOpen] = useState(false);

  const handleGroupCreated = () => {
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
        <NewGroupForm onGroupCreated={handleGroupCreated} />
      </DialogContent>
    </Dialog>
  );
}
