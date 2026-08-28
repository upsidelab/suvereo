import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center grow space-y-4 p-6 text-center">
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p className="text-muted-foreground">This page doesn't exist, or it isn't available to you.</p>
      <Link to="/" className="text-sm underline text-muted-foreground hover:text-foreground">
        Back to start
      </Link>
    </div>
  );
}
