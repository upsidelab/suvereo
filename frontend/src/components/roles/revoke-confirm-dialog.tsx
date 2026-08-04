import { Button } from "@/components/ui/button.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";

export interface RevokeConfirmDialogProps {
  open: boolean;
  title: string;
  count: number;
  unitLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

// Shared by GroupsList and DatasetRolesList: both warn how many things lose access before a
// delete, then cascade-revoke on confirm.
export function RevokeConfirmDialog({ open, title, count, unitLabel, onConfirm, onCancel }: RevokeConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onCancel(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-gray-600">
            {count > 0
              ? `This will revoke access for ${count} ${unitLabel}${count === 1 ? "" : "s"}. This action cannot be undone.`
              : "This action cannot be undone."}
          </p>
        </div>
        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button variant="destructive" onClick={onConfirm}>Delete</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
