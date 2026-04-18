"use client";

import { PlusIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import { loadTasks, type Task } from "@/core/tasks";
import { formatTimeAgo } from "@/core/utils/datetime";

export default function TasksPage() {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.title = `${t.tasks.pageTitle} - ${t.pages.appName}`;
    loadTasks()
      .then(setTasks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [t.tasks.pageTitle, t.pages.appName]);

  const activeTasks = useMemo(() => tasks.filter((t) => t.status === "active"), [tasks]);
  const pausedTasks = useMemo(() => tasks.filter((t) => t.status === "paused"), [tasks]);

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <Link href="/workspace/tasks/new">
          <Button size="sm" className="gap-2">
            <PlusIcon className="size-4" />
            {t.tasks.createTask}
          </Button>
        </Link>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="flex size-full flex-col">
          <main className="min-h-0 flex-1">
            <div className="mx-auto w-full max-w-(--container-width-md) py-8">
              {loading ? (
                <div className="text-center text-muted-foreground">{t.common.loading}</div>
              ) : tasks.length === 0 ? (
                <div className="text-center">
                  <p className="text-muted-foreground mb-4">{t.tasks.empty}</p>
                  <Link href="/workspace/tasks/new">
                    <Button>{t.tasks.createTask}</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-8">
                  {activeTasks.length > 0 && (
                    <section>
                      <h2 className="mb-4 text-lg font-semibold">{t.tasks.activeTasks}</h2>
                      <div className="space-y-2">
                        {activeTasks.map((task) => (
                          <TaskCard key={task.id} task={task} />
                        ))}
                      </div>
                    </section>
                  )}
                  {pausedTasks.length > 0 && (
                    <section>
                      <h2 className="mb-4 text-lg font-semibold">{t.tasks.pausedTasks}</h2>
                      <div className="space-y-2">
                        {pausedTasks.map((task) => (
                          <TaskCard key={task.id} task={task} />
                        ))}
                      </div>
                    </section>
                  )}
                </div>
              )}
            </div>
          </main>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}

function TaskCard({ task }: { task: Task }) {
  const { t } = useI18n();

  const triggerText = useMemo(() => {
    if (task.trigger_type === "cron" && task.trigger_config.cron) {
      return `Cron: ${task.trigger_config.cron}`;
    }
    if (task.trigger_type === "interval") {
      const cfg = task.trigger_config;
      if (cfg.interval_days) return `Every ${cfg.interval_days} days`;
      if (cfg.interval_hours) return `Every ${cfg.interval_hours} hours`;
      if (cfg.interval_minutes) return `Every ${cfg.interval_minutes} minutes`;
      return "Interval";
    }
    if (task.trigger_type === "one_time") {
      return "One time";
    }
    return task.trigger_type;
  }, [task.trigger_type, task.trigger_config]);

  return (
    <Link href={`/workspace/tasks/${task.id}`}>
      <div className="border rounded-lg p-4 transition-colors hover:bg-muted/50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">{task.name}</h3>
            {task.description && <p className="text-muted-foreground text-sm">{task.description}</p>}
          </div>
          <div className="text-right">
            <div
              className={`inline-flex items-center rounded-full px-2 py-1 text-xs ${
                task.status === "active"
                  ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                  : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
              }`}
            >
              {task.status === "active" ? t.tasks.statusActive : t.tasks.statusPaused}
            </div>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-between text-sm text-muted-foreground">
          <span>{triggerText}</span>
          {task.next_run_at && <span>{t.tasks.nextRun}: {formatTimeAgo(task.next_run_at)}</span>}
        </div>
      </div>
    </Link>
  );
}
