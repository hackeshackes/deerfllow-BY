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
import { useI18n } from "@/core/i18n/hooks";

const ASPECT_RATIOS = [
  { value: "16:9", labelKey: "wide" },
  { value: "4:3", labelKey: "standard" },
];

interface GenerateResponse {
  success: boolean;
  task_id: string | null;
  status: string;
  message: string;
  error: string | null;
}

export default function PPTPage() {
  const { t } = useI18n();
  const [topic, setTopic] = useState("");
  const [numSlides, setNumSlides] = useState(8);
  const [style, setStyle] = useState("gradient-modern");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = t.ppt.pageTitle;
  }, [t]);

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError(t.ppt.topicRequired);
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
        throw new Error(data.error ?? t.ppt.generateFailed);
      }

      window.location.href = `/api/ppt/download/${data.task_id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : t.ppt.generateFailed);
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
            {t.ppt.pageTitle}
          </div>

          <div className="space-y-6">
            <div>
              <label className="mb-2 block text-sm font-medium">{t.ppt.topic}</label>
              <Input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder={t.ppt.topicPlaceholder}
                disabled={isGenerating}
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">{t.ppt.numSlides}</label>
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
              <label className="mb-2 block text-sm font-medium">{t.ppt.designStyle}</label>
              <Select value={style} onValueChange={setStyle} disabled={isGenerating}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gradient-modern">
                    {t.ppt.styles.gradientModern} - {t.ppt.styles.gradientModernDesc}
                  </SelectItem>
                  <SelectItem value="dark-premium">
                    {t.ppt.styles.darkPremium} - {t.ppt.styles.darkPremiumDesc}
                  </SelectItem>
                  <SelectItem value="glassmorphism">
                    {t.ppt.styles.glassmorphism} - {t.ppt.styles.glassmorphismDesc}
                  </SelectItem>
                  <SelectItem value="keynote">
                    {t.ppt.styles.keynote} - {t.ppt.styles.keynoteDesc}
                  </SelectItem>
                  <SelectItem value="minimal-swiss">
                    {t.ppt.styles.minimalSwiss} - {t.ppt.styles.minimalSwissDesc}
                  </SelectItem>
                  <SelectItem value="consulting">
                    {t.ppt.styles.consulting} - {t.ppt.styles.consultingDesc}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">{t.ppt.slideRatio}</label>
              <Select value={aspectRatio} onValueChange={setAspectRatio} disabled={isGenerating}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASPECT_RATIOS.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {t.ppt.ratios[r.labelKey as keyof typeof t.ppt.ratios]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error && <div className="text-sm text-red-500">{error}</div>}

            <Button
              onClick={handleGenerate}
              disabled={isGenerating || !topic.trim()}
              className="w-full"
            >
              {isGenerating ? t.ppt.generating : t.ppt.generate}
            </Button>
          </div>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}