"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import { createTask, type CreateTaskRequest } from "@/core/tasks";

type Frequency = "daily" | "weekly" | "monthly" | "custom";

function buildCron(frequency: Frequency, time: string, weekday: string): string {
  const [hour = "9", minute = "0"] = time.split(":");
  if (frequency === "weekly") return `${minute} ${hour} * * ${weekday}`;
  if (frequency === "monthly") return `${minute} ${hour} 1 * *`;
  return `${minute} ${hour} * * *`;
}

export default function NewAutomationPage() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const workflow = searchParams.get("workflow");
  const titleParam = searchParams.get("title");
  const promptParam = searchParams.get("prompt");
  const [name, setName] = useState(
    titleParam ?? (workflow ? `${workflow} 自动化` : ""),
  );
  const [description, setDescription] = useState("");
  const [frequency, setFrequency] = useState<Frequency>("daily");
  const [time, setTime] = useState("09:00");
  const [weekday, setWeekday] = useState("1");
  const [customCron, setCustomCron] = useState("0 9 * * *");
  const [promptTemplate, setPromptTemplate] = useState(
    promptParam ?? (workflow ? `请使用 ${workflow} 工作流完成这项周期性任务。` : ""),
  );
  const [outputTarget, setOutputTarget] = useState("thread");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    document.title = t.automations.newAutomationTitle + " - MicX";
  }, [t.automations.newAutomationTitle]);

  const cronExpression = useMemo(() => {
    if (frequency === "custom") return customCron;
    return buildCron(frequency, time, weekday);
  }, [customCron, frequency, time, weekday]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !promptTemplate.trim()) {
      setError(t.automations.automationNameRequired);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const request: CreateTaskRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        trigger_type: "cron",
        trigger_config: {
          cron: cronExpression,
          timezone: "Asia/Shanghai",
        },
        prompt_template: promptTemplate.trim(),
        skill_names: workflow ? [workflow] : [],
        output_config: {
          save_to_thread: outputTarget !== "log",
          ...(outputTarget === "webhook" ? { webhook_url: "" } : {}),
        },
      };
      await createTask(request);
      router.push("/workspace/automations");
    } catch (err) {
      setError(t.automations.automationFailed);
      setSaving(false);
    }
  }

  return (
    <WorkspaceContainer>
      <WorkspaceHeader />
      <WorkspaceBody>
        <div className="mx-auto w-full max-w-3xl py-8">
          <h1 className="text-2xl font-bold">{t.automations.newAutomationTitle}</h1>
          <p className="text-muted-foreground mt-2 text-sm">
            {t.automations.newAutomationDescription}
          </p>

          {mounted ? (
          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="name">{t.automations.name}</label>
              <Input
                id="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t.automations.namePlaceholder}
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="description">{t.automations.descriptionLabel}</label>
              <Input
                id="description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder={t.automations.descriptionPlaceholder}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">{t.automations.frequency}</label>
                <Select value={frequency} onValueChange={(value) => setFrequency(value as Frequency)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">{t.automations.daily}</SelectItem>
                    <SelectItem value="weekly">{t.automations.weekly}</SelectItem>
                    <SelectItem value="monthly">{t.automations.monthly}</SelectItem>
                    <SelectItem value="custom">{t.automations.customCron}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {frequency !== "custom" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="time">{t.automations.time}</label>
                  <Input id="time" type="time" value={time} onChange={(event) => setTime(event.target.value)} />
                </div>
              )}
              {frequency === "weekly" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">{t.automations.weekday}</label>
                  <Select value={weekday} onValueChange={setWeekday}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">{t.automations.monday}</SelectItem>
                      <SelectItem value="2">{t.automations.tuesday}</SelectItem>
                      <SelectItem value="3">{t.automations.wednesday}</SelectItem>
                      <SelectItem value="4">{t.automations.thursday}</SelectItem>
                      <SelectItem value="5">{t.automations.friday}</SelectItem>
                      <SelectItem value="6">{t.automations.saturday}</SelectItem>
                      <SelectItem value="0">{t.automations.sunday}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            {frequency === "custom" && (
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="cron">{t.automations.customCron}</label>
                <Input id="cron" value={customCron} onChange={(event) => setCustomCron(event.target.value)} />
                <p className="text-muted-foreground text-xs">{t.automations.customCronGuidance}</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">{t.automations.outputLocation}</label>
              <Select value={outputTarget} onValueChange={setOutputTarget}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="thread">{t.automations.saveToThread}</SelectItem>
                  <SelectItem value="log">{t.automations.onlyLog}</SelectItem>
                  <SelectItem value="webhook">{t.automations.webhookLater}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="prompt">{t.automations.promptTask}</label>
              <Textarea
                id="prompt"
                value={promptTemplate}
                onChange={(event) => setPromptTemplate(event.target.value)}
                placeholder={t.automations.promptPlaceholder}
                rows={8}
                required
              />
            </div>

            {error && <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

            <div className="flex gap-3">
              <Button type="submit" disabled={saving}>{saving ? t.automations.saving : t.automations.saveAutomation}</Button>
              <Button type="button" variant="outline" onClick={() => router.back()}>{t.automations.cancel}</Button>
            </div>
          </form>
          ) : (
            <div className="text-muted-foreground mt-8 rounded-2xl border p-8 text-center text-sm">
              {t.automations.preparingForm}
            </div>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}