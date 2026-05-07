"use client";

import { PresentationIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";

const PPT_STYLES = [
  { value: "gradient-modern", label: "现代渐变", description: "适合创业公司、科技产品" },
  { value: "dark-premium", label: "深色高端", description: "适合高管汇报、奢华品牌" },
  { value: "glassmorphism", label: "玻璃拟态", description: "适合 AI/SaaS 产品演示" },
  { value: "keynote", label: "Keynote 风格", description: "Apple 主题演示" },
  { value: "minimal-swiss", label: "瑞士极简", description: "适合架构、设计演示" },
  { value: "consulting", label: "咨询风格", description: "适合商业咨询报告" },
];

const ASPECT_RATIOS = [
  { value: "16:9", label: "16:9 宽屏" },
  { value: "4:3", label: "4:3 标准" },
];

interface GenerateResponse {
  success: boolean;
  task_id: string | null;
  status: string;
  message: string;
  error: string | null;
}

export default function PPTPage() {
  const [topic, setTopic] = useState("");
  const [numSlides, setNumSlides] = useState(8);
  const [style, setStyle] = useState("gradient-modern");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = `演示生成 - MicX`;
  }, []);

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError("请输入 PPT 主题");
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const response = await fetch("/api/ppt/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic.trim(),
          num_slides: numSlides,
          style,
          aspect_ratio: aspectRatio,
        }),
      });

      const data: GenerateResponse = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error ?? "生成失败");
      }

      window.location.href = `/api/ppt/download/${data.task_id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <WorkspaceContainer>
      <WorkspaceHeader />
      <WorkspaceBody>
        <div className="mx-auto w-full max-w-2xl py-12">
          <div className="mb-8 flex items-center gap-3 text-2xl font-semibold">
            <PresentationIcon className="size-7" />
            演示生成
          </div>

          <div className="space-y-6">
            <div>
              <label className="mb-2 block text-sm font-medium">PPT 主题</label>
              <Input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="例如：2024年Q3产品迭代总结"
                disabled={isGenerating}
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">幻灯片数量</label>
              <Input
                type="number"
                min={3}
                max={20}
                value={numSlides}
                onChange={(e) => setNumSlides(parseInt(e.target.value) || 8)}
                disabled={isGenerating}
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">设计风格</label>
              <Select value={style} onValueChange={setStyle} disabled={isGenerating}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PPT_STYLES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label} - {s.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">幻灯片比例</label>
              <Select value={aspectRatio} onValueChange={setAspectRatio} disabled={isGenerating}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASPECT_RATIOS.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error && <div className="text-sm text-red-500">{error}</div>}

            <Button onClick={handleGenerate} disabled={isGenerating || !topic.trim()} className="w-full">
              {isGenerating ? "生成中..." : "生成 PPT"}
            </Button>
          </div>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
