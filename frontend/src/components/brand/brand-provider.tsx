"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { RuntimeBrand } from "@/core/brand/runtime";

const BrandContext = createContext<RuntimeBrand | null>(null);

export function BrandProvider({
  brand,
  children,
}: {
  brand: RuntimeBrand;
  children: React.ReactNode;
}) {
  const [runtimeBrand, setRuntimeBrand] = useState(brand);

  useEffect(() => {
    setRuntimeBrand(brand);
  }, [brand]);

  useEffect(() => {
    function handleBrandUpdate(event: Event) {
      const detail = (event as CustomEvent<RuntimeBrand>).detail;
      if (detail) {
        setRuntimeBrand(detail);
      }
    }

    window.addEventListener("micx-brand-updated", handleBrandUpdate as EventListener);
    return () => {
      window.removeEventListener("micx-brand-updated", handleBrandUpdate as EventListener);
    };
  }, []);

  const value = useMemo(() => runtimeBrand, [runtimeBrand]);

  return <BrandContext.Provider value={value}>{children}</BrandContext.Provider>;
}

export function useBrand() {
  const brand = useContext(BrandContext);
  if (!brand) {
    throw new Error("useBrand must be used within BrandProvider");
  }
  return brand;
}
