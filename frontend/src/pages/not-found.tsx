import { ArrowLeft, Compass } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="rounded-full bg-muted p-4 text-muted-foreground">
        <Compass className="h-8 w-8" />
      </div>
      <h1 className="mt-4 text-2xl font-semibold">Page not found</h1>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        The page you&apos;re looking for doesn&apos;t exist or was moved.
      </p>
      <Button asChild className="mt-6">
        <Link to="/">
          <ArrowLeft />
          Back to dashboard
        </Link>
      </Button>
    </div>
  );
}
