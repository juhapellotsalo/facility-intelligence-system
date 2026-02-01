import { useState, useEffect, type ReactNode } from "react";
import { Monitor } from "lucide-react";

const MIN_WIDTH = 1024;

interface ViewportGuardProps {
  children: ReactNode;
}

export function ViewportGuard({ children }: ViewportGuardProps) {
  const [isTooSmall, setIsTooSmall] = useState(false);

  useEffect(() => {
    const checkWidth = () => {
      setIsTooSmall(window.innerWidth < MIN_WIDTH);
    };

    // Check on mount
    checkWidth();

    // Listen for resize
    window.addEventListener("resize", checkWidth);
    return () => window.removeEventListener("resize", checkWidth);
  }, []);

  if (isTooSmall) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-bg-base p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-bg-surface">
          <Monitor className="h-8 w-8 text-text-muted" />
        </div>
        <div className="space-y-2">
          <h1 className="text-lg font-semibold text-text-primary">
            Larger screen required
          </h1>
          <p className="max-w-sm text-sm text-text-muted">
            Please use a screen at least {MIN_WIDTH}px wide to view the Facility
            Intelligence System.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
