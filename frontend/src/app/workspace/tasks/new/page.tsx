"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

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

export default function NewTaskPage() {
  const { t } = useI18n();
  const router = useRouter();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState<string>("cron");
  const [cronExpression, setCronExpression] = useState("0 9 * * *");
  const [intervalValue, setIntervalValue] = useState(1);
  const [intervalUnit, setIntervalUnit] = useState("days");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = `${t.tasks.createTask} - ${t.pages.appName}`;
  }, [t.tasks.createTask, t.pages.appName]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !promptTemplate.trim()) {
      setError("Name and prompt template are required");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const request: CreateTaskRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        trigger_type: triggerType,
        trigger_config: {
          cron: triggerType === "cron" ? cronExpression : undefined,
          interval_days: triggerType === "interval" && intervalUnit === "days" ? intervalValue : undefined,
          interval_hours: triggerType === "interval" && intervalUnit === "hours" ? intervalValue : undefined,
          interval_minutes: triggerType === "interval" && intervalUnit === "minutes" ? intervalValue : undefined,
          timezone: "Asia/Shanghai",
        },
        prompt_template: promptTemplate.trim(),
      };

      await createTask(request);
      router.push("/workspace/tasks");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
      setSaving(false);
    }
  };

  return (
    <WorkspaceContainer>
      <WorkspaceHeader />
      <WorkspaceBody>
        <div className="flex size-full flex-col">
          <main className="min-h-0 flex-1">
            <div className="mx-auto w-full max-w-(--container-width-md) py-8">
              <h1 className="mb-8 text-2xl font-bold">{t.tasks.createTask}</h1>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="name">{t.tasks.name}</label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={t.tasks.namePlaceholder}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="description">{t.tasks.description}</label>
                  <Input
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder={t.tasks.descriptionPlaceholder}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="triggerType">{t.tasks.triggerType}</label>
                  <Select value={triggerType} onValueChange={setTriggerType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cron">{t.tasks.cron}</SelectItem>
                      <SelectItem value="interval">{t.tasks.interval}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {triggerType === "cron" && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium" htmlFor="cron">{t.tasks.cronExpression}</label>
                    <Input
                      id="cron"
                      value={cronExpression}
                      onChange={(e) => setCronExpression(e.target.value)}
                      placeholder={t.tasks.cronPlaceholder}
                      required={triggerType === "cron"}
                    />
                    <p className="text-muted-foreground text-sm">
                      Format: minute hour day month weekday
                    </p>
                  </div>
                )}

                {triggerType === "interval" && (
                  <div className="flex gap-4">
                    <div className="flex-1 space-y-2">
                      <label className="text-sm font-medium" htmlFor="intervalValue">{t.tasks.intervalUnit}</label>
                      <Input
                        id="intervalValue"
                        type="number"
                        min={1}
                        value={intervalValue}
                        onChange={(e) => setIntervalValue(parseInt(e.target.value) || 1)}
                      />
                    </div>
                    <div className="flex-1 space-y-2">
                      <label className="text-sm font-medium" htmlFor="intervalUnit">&nbsp;</label>
                      <Select value={intervalUnit} onValueChange={setIntervalUnit}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="minutes">{t.tasks.minutes}</SelectItem>
                          <SelectItem value="hours">{t.tasks.hours}</SelectItem>
                          <SelectItem value="days">{t.tasks.days}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="prompt">{t.tasks.promptTemplate}</label>
                  <Textarea
                    id="prompt"
                    value={promptTemplate}
                    onChange={(e) => setPromptTemplate(e.target.value)}
                    placeholder={t.tasks.promptPlaceholder}
                    rows={6}
                    required
                  />
                </div>

                {error && (
                  <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                    {error}
                  </div>
                )}

                <div className="flex gap-4">
                  <Button type="submit" disabled={saving}>
                    {saving ? t.common.loading : t.tasks.saveTask}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => router.back()}
                  >
                    {t.common.cancel}
                  </Button>
                </div>
              </form>
            </div>
          </main>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
