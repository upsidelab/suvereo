import { RevokeConfirmDialog } from "@/components/roles/revoke-confirm-dialog.tsx";

export interface RevokeOwnAdminAccessDialogProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function RevokeOwnAdminAccessDialog({ open, onConfirm, onCancel }: RevokeOwnAdminAccessDialogProps) {
  return (
    <RevokeConfirmDialog
      open={open}
      title="Revoke your own admin access?"
      confirmLabel="Revoke my admin access"
      description={"This revokes your own admin access. You'll lose the Manage section immediately, and only "
        + "another admin or a server shell can restore it."}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}
