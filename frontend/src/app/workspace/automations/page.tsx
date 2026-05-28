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
import { useI18n } from "@/core/i18n/hooks";
import { loadTasks, type Task } from "@/core/tasks";
import { formatTimeAgo } from "@/core/utils/datetime";

function describeTrigger(task: Task, t: ReturnType<typeof useI18n>["t"]): string {
  const config = task.trigger_config;
  if (task.trigger_type === "cron" && config.cron) {
    const [minute, hour, dayOfMonth, month, dayOfWeek] = config.cron.split(" ");
    if (dayOfMonth === "*" && month === "*" && dayOfWeek === "*") {
      return `${t.automations.daily} ${hour?.padStart(2, "0")}:${minute?.padStart(2, "0")}`;
    }
    if (dayOfMonth === "*" && month === "*" && dayOfWeek && dayOfWeek !== "*") {
      return `${t.automations.weekly} ${dayOfWeek} ${hour?.padStart(2, "0")}:${minute?.padStart(2, "0")}`;
    }
    return `${t.automations.customSchedule} ${config.cron}`;
  }
  if (task.trigger_type === "interval") {
    if (config.interval_days) return t.automations.everyXDays(config.interval_days);
    if (config.interval_hours) return t.automations.everyXHours(config.interval_hours);
    if (config.interval_minutes) return t.automations.everyXMinutes(config.interval_minutes);
  }
  return t.automations.manualOrOnce;
}

function outputLabel(task: Task, t: ReturnType<typeof useI18n>["t"]): string {
  if (task.thread_id) return t.automations.outputToThread;
  if (task.output_config.webhook_url) return t.automations.outputToWebhook;
  return task.output_config.save_to_thread ? t.automations.outputToNewThread : t.automations.logOnly;
}

export default function AutomationsPage() {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.title = `${t.sidebar.automations} - MicX`;
    loadTasks()
      .then(setTasks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [t]);

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
            {t.automations.createAutomation}
          </Button>
        </Link>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 py-8">
          <div>
            <div className="flex items-center gap-2 text-2xl font-semibold">
              <RepeatIcon className="size-6" />
              {t.sidebar.automations}
            </div>
            <p className="text-muted-foreground mt-2 text-sm">
              {t.automations.description}
            </p>
          </div>

          {loading ? (
            <div className="text-muted-foreground text-center">{t.common.loading}</div>
          ) : tasks.length === 0 ? (
            <div className="rounded-2xl border py-12 text-center">
              <p className="text-muted-foreground mb-4">{t.automations.empty}</p>
              <Link href="/workspace/automations/new">
                <Button>{t.automations.createFirstAutomation}</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-8">
              {activeTasks.length > 0 && (
                <AutomationSection title={t.tasks.statusActive} tasks={activeTasks} t={t} />
              )}
              {pausedTasks.length > 0 && (
                <AutomationSection title={t.tasks.statusPaused} tasks={pausedTasks} t={t} />
              )}
            </div>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}

function AutomationSection({ title, tasks, t }: { title: string; tasks: Task[]; t: ReturnType<typeof useI18n>["t"] }) {
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
                  {task.status === "active" ? t.tasks.statusActive : t.tasks.statusPaused}
                </Badge>
              </div>
              <div className="text-muted-foreground mt-3 flex flex-wrap gap-3 text-sm">
                <span className="inline-flex items-center gap-1">
                  <ClockIcon className="size-3.5" />
                  {describeTrigger(task, t)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageCircleIcon className="size-3.5" />
                  {outputLabel(task, t)}
                </span>
                {task.next_run_at && <span>{t.automations.nextRun}{formatTimeAgo(task.next_run_at)}</span>}
                {task.last_run_at && <span>{t.automations.lastRun}{formatTimeAgo(task.last_run_at)}</span>}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
