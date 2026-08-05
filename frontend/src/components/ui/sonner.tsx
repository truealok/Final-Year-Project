import { Toaster as Sonner } from "sonner";

import { useTheme } from "@/hooks/use-theme";

type ToasterProps = React.ComponentProps<typeof Sonner>;

/** Toast host themed to match the application. */
export function Toaster(props: ToasterProps) {
  const { resolvedTheme } = useTheme();

  return (
    <Sonner
      theme={resolvedTheme}
      position="top-right"
      toastOptions={{
        classNames: {
          toast:
            "group border-border bg-card text-card-foreground shadow-card-hover",
          description: "text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}
