import { Button } from "@/components/ui/button.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";

export interface RevokeConfirmDialogProps {
  open: boolean;
  title: string;
  count?: number;
  unitLabel?: string;
  confirmLabel?: string;
  description?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function RevokeConfirmDialog({
  open,
  title,
  count,
  unitLabel,
  confirmLabel = "Delete",
  description,
  onConfirm,
  onCancel,
}: RevokeConfirmDialogProps) {
  const countSentence = count !== undefined && count > 0 && unitLabel
    ? `This will revoke access for ${count} ${unitLabel}${count === 1 ? "" : "s"}. `
    : "";

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onCancel(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-gray-600">
            {description ?? `${countSentence}This action cannot be undone.`}
          </p>
        </div>
        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button variant="destructive" onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
