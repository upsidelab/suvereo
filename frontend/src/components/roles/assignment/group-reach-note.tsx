export interface GroupReachNoteProps {
  memberCount: number;
}

export function GroupReachNote({ memberCount }: GroupReachNoteProps) {
  return (
    <p className="text-sm text-muted-foreground mb-4">
      Everything granted here reaches{" "}
      {memberCount === 1 ? "the 1 member" : `all ${memberCount} members`} of this group,
      and anyone added to it later.
    </p>
  );
}
