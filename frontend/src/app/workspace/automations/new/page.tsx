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
import { createTask, type CreateTaskRequest } from "@/core/tasks";

type Frequency = "daily" | "weekly" | "monthly" | "custom";

function buildCron(frequency: Frequency, time: string, weekday: string): string {
  const [hour = "9", minute = "0"] = time.split(":");
  if (frequency === "weekly") return `${minute} ${hour} * * ${weekday}`;
  if (frequency === "monthly") return `${minute} ${hour} 1 * *`;
  return `${minute} ${hour} * * *`;
}

export default function NewAutomationPage() {
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
    document.title = "创建自动化 - MicX";
  }, []);

  const cronExpression = useMemo(() => {
    if (frequency === "custom") return customCron;
    return buildCron(frequency, time, weekday);
  }, [customCron, frequency, time, weekday]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !promptTemplate.trim()) {
      setError("请填写自动化名称和要执行的任务内容。");
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
      setError(err instanceof Error ? err.message : "创建自动化失败");
      setSaving(false);
    }
  }

  return (
    <WorkspaceContainer>
      <WorkspaceHeader />
      <WorkspaceBody>
        <div className="mx-auto w-full max-w-3xl py-8">
          <h1 className="text-2xl font-bold">创建自动化</h1>
          <p className="text-muted-foreground mt-2 text-sm">
            用自然语言描述 AI 要定期完成的工作，再选择运行时间和输出位置。
          </p>

          {mounted ? (
          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="name">名称</label>
              <Input
                id="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="例如：每日晨报"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="description">说明</label>
              <Input
                id="description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="这项自动化会帮你做什么"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">运行频率</label>
                <Select value={frequency} onValueChange={(value) => setFrequency(value as Frequency)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">每天</SelectItem>
                    <SelectItem value="weekly">每周</SelectItem>
                    <SelectItem value="monthly">每月</SelectItem>
                    <SelectItem value="custom">自定义时间规则</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {frequency !== "custom" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="time">运行时间</label>
                  <Input id="time" type="time" value={time} onChange={(event) => setTime(event.target.value)} />
                </div>
              )}
              {frequency === "weekly" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">星期</label>
                  <Select value={weekday} onValueChange={setWeekday}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">周一</SelectItem>
                      <SelectItem value="2">周二</SelectItem>
                      <SelectItem value="3">周三</SelectItem>
                      <SelectItem value="4">周四</SelectItem>
                      <SelectItem value="5">周五</SelectItem>
                      <SelectItem value="6">周六</SelectItem>
                      <SelectItem value="0">周日</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            {frequency === "custom" && (
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="cron">自定义时间规则</label>
                <Input id="cron" value={customCron} onChange={(event) => setCustomCron(event.target.value)} />
                <p className="text-muted-foreground text-xs">高级模式，使用 Cron 表达式。</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">输出位置</label>
              <Select value={outputTarget} onValueChange={setOutputTarget}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="thread">保存到对话</SelectItem>
                  <SelectItem value="log">仅保存执行记录</SelectItem>
                  <SelectItem value="webhook">Webhook（稍后配置）</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="prompt">让 AI 做什么</label>
              <Textarea
                id="prompt"
                value={promptTemplate}
                onChange={(event) => setPromptTemplate(event.target.value)}
                placeholder="例如：每天早上总结今天的日程、待办和需要重点关注的事项。"
                rows={8}
                required
              />
            </div>

            {error && <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

            <div className="flex gap-3">
              <Button type="submit" disabled={saving}>{saving ? "保存中..." : "保存自动化"}</Button>
              <Button type="button" variant="outline" onClick={() => router.back()}>取消</Button>
            </div>
          </form>
          ) : (
            <div className="text-muted-foreground mt-8 rounded-2xl border p-8 text-center text-sm">
              正在准备自动化表单...
            </div>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
