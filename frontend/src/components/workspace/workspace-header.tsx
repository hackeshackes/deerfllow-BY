"use client";

import Link from "next/link";

import { BrandMark } from "@/components/brand/brand-mark";
import { useBrand } from "@/components/brand/brand-provider";
import {
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { env } from "@/env";
import { cn } from "@/lib/utils";

export function WorkspaceHeader({ className }: { className?: string }) {
  const brand = useBrand();
  const { state } = useSidebar();
  return (
    <div
      className={cn(
        "group/workspace-header flex h-12 flex-col justify-center",
        className,
      )}
    >
        {state === "collapsed" ? (
            <div className="group-has-data-[collapsible=icon]/sidebar-wrapper:-translate-y flex w-full cursor-pointer items-center justify-center">
              <div className="text-primary block pt-1 font-serif group-hover/workspace-header:hidden">
                {brand.shortName}
              </div>
            <SidebarTrigger className="hidden pl-2 group-hover/workspace-header:block" />
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2">
            {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ? (
              <Link href="/" className="ml-2">
                <BrandMark compact />
              </Link>
            ) : (
              <div className="ml-2 cursor-default">
                <BrandMark compact />
              </div>
            )}
            <SidebarTrigger />
          </div>
        )}
    </div>
  );
}
