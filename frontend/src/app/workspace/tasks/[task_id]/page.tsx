"use client";

import { EditIcon, PauseIcon, PlayIcon, TrashIcon } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
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
import { Textarea } from "@/components/ui/textarea";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import {
  deleteTask,
  getTask,
  getTaskExecutions,
  pauseTask,
  resumeTask,
  runTaskNow,
  updateTask,
  type Task,
  type TaskExecution,
  type UpdateTaskRequest,
} from "@/core/tasks";
import { formatTimeAgo } from "@/core/utils/datetime";

export default function TaskDetailPage() {
  const { t } = useI18n();
  const params = useParams();
  const router = useRouter();
  const taskId = params.task_id as string;

  const [task, setTask] = useState<Task | null>(null);
  const [executions, setExecutions] = useState<TaskExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [promptTemplate, setPromptTemplate] = useState("");

  const [editingTrigger, setEditingTrigger] = useState(false);
  const [triggerType, setTriggerType] = useState<string>("cron");
  const [cronExpression, setCronExpression] = useState("0 9 * * *");
  const [intervalValue, setIntervalValue] = useState(1);
  const [intervalUnit, setIntervalUnit] = useState("days");

  useEffect(() => {
    document.title = task ? `${task.name} - ${t.tasks.pageTitle}` : t.tasks.pageTitle;
  }, [task, t.tasks.pageTitle]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [taskData, executionsData] = await Promise.all([
          getTask(taskId),
          getTaskExecutions(taskId),
        ]);
        setTask(taskData);
        setExecutions(executionsData);
        setName(taskData.name);
        setDescription(taskData.description ?? "");
        setPromptTemplate(taskData.prompt_template);
        setTriggerType(taskData.trigger_type);
        if (taskData.trigger_type === "cron") {
          setCronExpression(taskData.trigger_config.cron ?? "0 9 * * *");
        } else if (taskData.trigger_type === "interval") {
          if (taskData.trigger_config.interval_days) {
            setIntervalValue(taskData.trigger_config.interval_days);
            setIntervalUnit("days");
          } else if (taskData.trigger_config.interval_hours) {
            setIntervalValue(taskData.trigger_config.interval_hours);
            setIntervalUnit("hours");
          } else if (taskData.trigger_config.interval_minutes) {
            setIntervalValue(taskData.trigger_config.interval_minutes);
            setIntervalUnit("minutes");
          }
        }
      } catch (err) {
        console.error("Failed to load task:", err);
      } finally {
        setLoading(false);
      }
    };
    loadData().catch(console.error);
  }, [taskId]);

  const handleSave = async () => {
    if (!name.trim() || !promptTemplate.trim()) return;

    setSaving(true);
    try {
      const request: UpdateTaskRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        prompt_template: promptTemplate.trim(),
      };
      const updated = await updateTask(taskId, request);
      setTask(updated);
    } catch (err) {
      console.error("Failed to update task:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTrigger = async () => {
    setSaving(true);
    try {
      const request: UpdateTaskRequest = {
        trigger_type: triggerType,
        trigger_config: {
          cron: triggerType === "cron" ? cronExpression : undefined,
          interval_days: triggerType === "interval" && intervalUnit === "days" ? intervalValue : undefined,
          interval_hours: triggerType === "interval" && intervalUnit === "hours" ? intervalValue : undefined,
          interval_minutes: triggerType === "interval" && intervalUnit === "minutes" ? intervalValue : undefined,
          timezone: "Asia/Shanghai",
        },
      };
      const updated = await updateTask(taskId, request);
      setTask(updated);
      setEditingTrigger(false);
    } catch (err) {
      console.error("Failed to update trigger:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleRunNow = async () => {
    try {
      const execution = await runTaskNow(taskId);
      setExecutions((prev) => [execution, ...prev]);
    } catch (err) {
      console.error("Failed to run task:", err);
    }
  };

  const handlePause = async () => {
    try {
      const updated = await pauseTask(taskId);
      setTask(updated);
    } catch (err) {
      console.error("Failed to pause task:", err);
    }
  };

  const handleResume = async () => {
    try {
      const updated = await resumeTask(taskId);
      setTask(updated);
    } catch (err) {
      console.error("Failed to resume task:", err);
    }
  };

  const handleDelete = async () => {
    if (!confirm(t.tasks.deleteConfirm)) return;

    setDeleting(true);
    try {
      await deleteTask(taskId);
      router.push("/workspace/tasks");
    } catch (err) {
      console.error("Failed to delete task:", err);
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <WorkspaceContainer>
        <WorkspaceHeader />
        <WorkspaceBody>
          <div className="flex items-center justify-center py-8">
            {t.common.loading}
          </div>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  if (!task) {
    return (
      <WorkspaceContainer>
        <WorkspaceHeader />
        <WorkspaceBody>
          <div className="text-center py-8">Task not found</div>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <div className="flex gap-2">
          {task.status === "active" ? (
            <Button size="sm" variant="outline" onClick={handlePause}>
              <PauseIcon className="size-4 mr-1" />
              {t.tasks.pause}
            </Button>
          ) : (
            <Button size="sm" variant="outline" onClick={handleResume}>
              <PlayIcon className="size-4 mr-1" />
              {t.tasks.resume}
            </Button>
          )}
          <Button size="sm" onClick={handleRunNow}>
            <PlayIcon className="size-4 mr-1" />
            {t.tasks.runNow}
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={handleDelete}
            disabled={deleting}
          >
            <TrashIcon className="size-4 mr-1" />
            {t.tasks.delete}
          </Button>
        </div>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="flex size-full flex-col">
          <main className="min-h-0 flex-1">
            <div className="mx-auto w-full max-w-(--container-width-md) py-8 space-y-8">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="name">{t.tasks.name}</label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="description">{t.tasks.description}</label>
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="rounded-lg border p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium">{t.tasks.triggerType}</h3>
                  {!editingTrigger && (
                    <Button size="sm" variant="ghost" onClick={() => setEditingTrigger(true)}>
                      <EditIcon className="size-4 mr-1" />
                      {t.common.edit}
                    </Button>
                  )}
                </div>

                {editingTrigger ? (
                  <div className="space-y-4">
                    <Select value={triggerType} onValueChange={setTriggerType}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="cron">{t.tasks.cron}</SelectItem>
                        <SelectItem value="interval">{t.tasks.interval}</SelectItem>
                      </SelectContent>
                    </Select>

                    {triggerType === "cron" && (
                      <div className="space-y-2">
                        <Input
                          value={cronExpression}
                          onChange={(e) => setCronExpression(e.target.value)}
                          placeholder={t.tasks.cronPlaceholder}
                        />
                        <p className="text-muted-foreground text-sm">
                          {t.tasks.cronGuidance}
                        </p>
                      </div>
                    )}

                    {triggerType === "interval" && (
                      <div className="flex gap-4">
                        <div className="flex-1 space-y-2">
                          <Input
                            type="number"
                            min={1}
                            value={intervalValue}
                            onChange={(e) => setIntervalValue(parseInt(e.target.value) || 1)}
                          />
                        </div>
                        <div className="flex-1 space-y-2">
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

                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleSaveTrigger} disabled={saving}>
                        {saving ? t.common.loading : t.common.save}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setEditingTrigger(false)}>
                        {t.common.cancel}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="text-sm text-muted-foreground">
                      {task.trigger_type === "cron" && `Cron: ${task.trigger_config.cron}`}
                      {task.trigger_type === "interval" && `Interval: ${task.trigger_config.interval_days ? `${task.trigger_config.interval_days} days` : task.trigger_config.interval_hours ? `${task.trigger_config.interval_hours} hours` : task.trigger_config.interval_minutes ? `${task.trigger_config.interval_minutes} minutes` : "Interval"}`}
                      {task.trigger_type === "one_time" && "One time"}
                    </div>
                    {task.next_run_at && (
                      <div className="text-sm mt-1">
                        {t.tasks.nextRun}: {formatTimeAgo(task.next_run_at)}
                      </div>
                    )}
                  </>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="prompt">{t.tasks.promptTemplate}</label>
                <Textarea
                  id="prompt"
                  value={promptTemplate}
                  onChange={(e) => setPromptTemplate(e.target.value)}
                  rows={6}
                />
              </div>

              <Button onClick={handleSave} disabled={saving}>
                {saving ? t.common.loading : t.tasks.saveTask}
              </Button>

              <div className="space-y-4">
                <h3 className="text-lg font-medium">{t.tasks.executionHistory}</h3>
                {executions.length === 0 ? (
                  <p className="text-muted-foreground">{t.tasks.noExecutions}</p>
                ) : (
                  <div className="space-y-2">
                    {executions.map((exec) => (
                      <div key={exec.id} className="rounded-lg border p-4">
                        <div className="flex items-center justify-between">
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-1 text-xs ${
                              exec.status === "success"
                                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                                : exec.status === "failed"
                                  ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"
                                  : exec.status === "running"
                                    ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                                    : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
                            }`}
                          >
                            {t.tasks.executionStatus[exec.status as keyof typeof t.tasks.executionStatus]}
                          </span>
                          {exec.started_at && (
                            <span className="text-sm text-muted-foreground">
                              {formatTimeAgo(exec.started_at)}
                            </span>
                          )}
                        </div>
                        {exec.result_summary && (
                          <div className="mt-2 text-sm whitespace-pre-wrap">{exec.result_summary}</div>
                        )}
                        {exec.error_message && (
                          <p className="mt-2 text-sm text-destructive">{exec.error_message}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
