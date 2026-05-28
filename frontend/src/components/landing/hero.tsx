"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";

import { BrandMark } from "@/components/brand/brand-mark";
import { useBrand } from "@/components/brand/brand-provider";
import { Button } from "@/components/ui/button";
import { FlickeringGrid } from "@/components/ui/flickering-grid";
import Galaxy from "@/components/ui/galaxy";
import { WordRotate } from "@/components/ui/word-rotate";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

export function Hero({ className }: { className?: string }) {
  const brand = useBrand();
  const { t } = useI18n();
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
              "深度研究",
              "收集资料",
              "分析数据",
              "生成网页",
              "辅助开发",
              "生成演示稿",
              "生成图片",
              "生成播客",
              "生成视频",
              "生成内容",
              "整理邮件",
              "处理复杂任务",
              "快速学习新主题",
            ]}
          />{" "}
          <div>尽在 {brand.name}</div>
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
              <span className="text-md">{t.landing.enterWorkspace}</span>
              <ChevronRightIcon className="size-4" />
            </Button>
          </Link>
          <Link href={brand.docsPath}>
            <Button
              className="rounded-full border-white/20 bg-white/5 px-6 text-white hover:bg-white/10"
              size="lg"
              variant="outline"
            >
              {t.landing.viewDocs}
            </Button>
          </Link>
        </div>
        <div className="mt-10 grid gap-3 text-sm text-slate-300 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
            {t.landing.featureStreamingExecution}
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
            {t.landing.featureFileUpload}
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
            {t.landing.featureCollaboration}
          </div>
        </div>
      </div>
    </div>
  );
}
