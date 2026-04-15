"use client";

import { useBrand } from "@/components/brand/brand-provider";
import { cn } from "@/lib/utils";

export function BrandMark({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
  const brand = useBrand();
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="from-primary to-primary/70 text-primary-foreground flex size-9 items-center justify-center rounded-2xl bg-linear-to-br text-sm font-semibold shadow-lg shadow-black/10">
        {brand.shortName}
      </div>
      {!compact && (
        <div className="flex flex-col leading-none">
          <span className="text-foreground text-base font-semibold tracking-tight">
            {brand.name}
          </span>
          <span className="text-muted-foreground text-xs">
            {brand.tagline}
          </span>
        </div>
      )}
    </div>
  );
}
