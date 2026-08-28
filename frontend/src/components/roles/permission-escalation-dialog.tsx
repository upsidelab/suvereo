import { Button } from "@/components/ui/button.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";
import { EscalationWarning, PermissionEntity } from "@/lib/permissions/types.ts";
import { PermissionLabel } from "@/components/roles/permission-label.tsx";

export interface PermissionEscalationDialogProps {
  open: boolean;
  warnings: EscalationWarning[];
  entities: PermissionEntity[];
  onConfirm: () => void;
  onCancel: () => void;
}

export function PermissionEscalationDialog({
  open,
  warnings,
  entities,
  onConfirm,
  onCancel,
}: PermissionEscalationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onCancel(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Grant these permissions?</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {warnings.map((warning) => (
            <div key={warning.message} className="space-y-1">
              <p className="text-sm space-x-1">
                {warning.codes.map((code) => (
                  <PermissionLabel key={code} code={code} entities={entities} />
                ))}
              </p>
              <p className="text-sm text-gray-600">{warning.message}</p>
            </div>
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
