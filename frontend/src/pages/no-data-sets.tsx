export function NoDataSets() {
  return (
    <div className="flex flex-col items-center justify-center grow space-y-4 p-6 text-center">
      <h1 className="text-2xl font-bold">You don't have access to any data sets yet.</h1>
      <p className="text-muted-foreground">Please contact your administrator to request access.</p>
    </div>
  );
}
