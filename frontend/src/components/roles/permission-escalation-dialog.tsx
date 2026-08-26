import { Button } from "@/components/ui/button.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";

export interface PermissionEscalationDialogProps {
  open: boolean;
  warnings: string[];
  onConfirm: () => void;
  onCancel: () => void;
}


export function PermissionEscalationDialog({ open, warnings, onConfirm, onCancel }: PermissionEscalationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onCancel(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Grant these permissions?</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-4">
          {warnings.map((warning) => (
            <p key={warning} className="text-sm text-gray-600">{warning}</p>
          ))}
        </div>
        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button onClick={onConfirm}>Save anyway</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
