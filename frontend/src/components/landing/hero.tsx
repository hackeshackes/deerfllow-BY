"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";

import { BrandMark } from "@/components/brand/brand-mark";
import { Button } from "@/components/ui/button";
import { FlickeringGrid } from "@/components/ui/flickering-grid";
import Galaxy from "@/components/ui/galaxy";
import { WordRotate } from "@/components/ui/word-rotate";
import { brand } from "@/core/brand/config";
import { cn } from "@/lib/utils";

export function Hero({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex size-full flex-col items-center justify-center",
        className,
      )}
    >
      <div className="absolute inset-0 z-0 bg-black/40">
        <Galaxy
          mouseRepulsion={false}
          starSpeed={0.2}
          density={0.6}
          glowIntensity={0.35}
          twinkleIntensity={0.3}
          speed={0.5}
        />
      </div>
      <FlickeringGrid
        className="absolute inset-0 z-0 translate-y-8 opacity-60"
        squareSize={4}
        gridGap={4}
        color={"white"}
        maxOpacity={0.3}
        flickerChance={0.25}
      />
      <div className="container-md relative z-10 mx-auto flex h-screen flex-col items-center justify-center px-6">
        <BrandMark className="mb-6 text-white" />
        <h1 className="flex max-w-5xl flex-wrap items-center justify-center gap-3 text-center text-4xl font-bold md:text-6xl">
          <WordRotate
            words={[
              "Deep Research",
              "Collect Data",
              "Analyze Data",
              "Generate Webpages",
              "Vibe Coding",
              "Generate Slides",
              "Generate Images",
              "Generate Podcasts",
              "Generate Videos",
              "Generate Songs",
              "Organize Emails",
              "Do Anything",
              "Learn Anything",
            ]}
          />{" "}
          <div>with {brand.name}</div>
        </h1>
        <p className="mt-8 max-w-4xl text-center text-xl leading-9 text-slate-300 text-shadow-sm md:text-2xl">
          {brand.description}
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link href="/sign-in">
            <Button
              className="size-lg scale-108 rounded-full bg-white px-6 text-slate-950 hover:bg-cyan-50"
              size="lg"
            >
              <span className="text-md">Open private workspace</span>
              <ChevronRightIcon className="size-4" />
            </Button>
          </Link>
          <Link href="/en/docs">
            <Button
              className="rounded-full border-white/20 bg-white/5 px-6 text-white hover:bg-white/10"
              size="lg"
              variant="outline"
            >
              Read docs
            </Button>
          </Link>
        </div>
        <div className="mt-10 grid gap-3 text-sm text-slate-300 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
            Streamed agent runs with structured progress
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
            Uploads, artifacts, and export-friendly outputs
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
            Protected single-user workspace with owner access
          </div>
        </div>
      </div>
    </div>
  );
}
