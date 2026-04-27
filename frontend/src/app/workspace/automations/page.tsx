"use client";

import { ClockIcon, MessageCircleIcon, PlusIcon, RepeatIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { loadTasks, type Task } from "@/core/tasks";
import { formatTimeAgo } from "@/core/utils/datetime";

function describeTrigger(task: Task): string {
  const config = task.trigger_config;
  if (task.trigger_type === "cron" && config.cron) {
    const [minute, hour, dayOfMonth, month, dayOfWeek] = config.cron.split(" ");
    if (dayOfMonth === "*" && month === "*" && dayOfWeek === "*") {
      return `每天 ${hour?.padStart(2, "0")}:${minute?.padStart(2, "0")}`;
    }
    if (dayOfMonth === "*" && month === "*" && dayOfWeek && dayOfWeek !== "*") {
      return `每周 ${dayOfWeek} ${hour?.padStart(2, "0")}:${minute?.padStart(2, "0")}`;
    }
    return `自定义时间规则：${config.cron}`;
  }
  if (task.trigger_type === "interval") {
    if (config.interval_days) return `每 ${config.interval_days} 天`;
    if (config.interval_hours) return `每 ${config.interval_hours} 小时`;
    if (config.interval_minutes) return `每 ${config.interval_minutes} 分钟`;
  }
  return "手动或一次性运行";
}

function outputLabel(task: Task): string {
  if (task.thread_id) return "输出到关联对话";
  if (task.output_config.webhook_url) return "输出到 Webhook";
  return task.output_config.save_to_thread ? "输出到新对话" : "仅记录执行结果";
}

export default function AutomationsPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.title = "自动化 - MicX";
    loadTasks()
      .then(setTasks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const activeTasks = useMemo(
    () => tasks.filter((task) => task.status === "active"),
    [tasks],
  );
  const pausedTasks = useMemo(
    () => tasks.filter((task) => task.status === "paused"),
    [tasks],
  );

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <Link href="/workspace/automations/new">
          <Button size="sm" className="gap-2">
            <PlusIcon className="size-4" />
            创建自动化
          </Button>
        </Link>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 py-8">
          <div>
            <div className="flex items-center gap-2 text-2xl font-semibold">
              <RepeatIcon className="size-6" />
              自动化
            </div>
            <p className="text-muted-foreground mt-2 text-sm">
              设置固定时间让 AI 自动完成例行工作，并把结果写回个人或共享空间。
            </p>
          </div>

          {loading ? (
            <div className="text-muted-foreground text-center">加载中...</div>
          ) : tasks.length === 0 ? (
            <div className="rounded-2xl border py-12 text-center">
              <p className="text-muted-foreground mb-4">还没有自动化。</p>
              <Link href="/workspace/automations/new">
                <Button>创建第一个自动化</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-8">
              {activeTasks.length > 0 && (
                <AutomationSection title="运行中" tasks={activeTasks} />
              )}
              {pausedTasks.length > 0 && (
                <AutomationSection title="已暂停" tasks={pausedTasks} />
              )}
            </div>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}

function AutomationSection({ title, tasks }: { title: string; tasks: Task[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="space-y-3">
        {tasks.map((task) => (
          <Link key={task.id} href={`/workspace/tasks/${task.id}`}>
            <div className="rounded-2xl border p-4 transition-colors hover:bg-muted/50">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-medium">{task.name}</div>
                  {task.description && (
                    <p className="text-muted-foreground mt-1 text-sm">
                      {task.description}
                    </p>
                  )}
                </div>
                <Badge variant={task.status === "active" ? "default" : "outline"}>
                  {task.status === "active" ? "运行中" : "已暂停"}
                </Badge>
              </div>
              <div className="text-muted-foreground mt-3 flex flex-wrap gap-3 text-sm">
                <span className="inline-flex items-center gap-1">
                  <ClockIcon className="size-3.5" />
                  {describeTrigger(task)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageCircleIcon className="size-3.5" />
                  {outputLabel(task)}
                </span>
                {task.next_run_at && <span>下次：{formatTimeAgo(task.next_run_at)}</span>}
                {task.last_run_at && <span>上次：{formatTimeAgo(task.last_run_at)}</span>}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
