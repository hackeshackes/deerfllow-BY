"use client";

import { Calendar, Clock, MessageCircle, MoreHorizontal, Pause, Play } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";
import { pauseTask, resumeTask, type Task } from "@/core/tasks/api";
import { useScheduledTasks } from "@/core/tasks/hooks";

function formatNextRun(nextRunAt?: string, t?: ReturnType<typeof useI18n>["t"]): string {
  if (!nextRunAt) return t?.tasks.notSet ?? "Not set";
  const date = new Date(nextRunAt);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMs < 0) return t?.tasks.expired ?? "Expired";
  if (diffMins < 60) return t?.tasks.inMinutes(diffMins) ?? `${diffMins} minutes`;
  if (diffHours < 24) return t?.tasks.inHours(diffHours) ?? `${diffHours} hours`;
  if (diffDays < 7) return t?.tasks.inDays(diffDays) ?? `${diffDays} days`;
  return date.toLocaleDateString("zh-CN");
}

function getTaskLink(task: Task): string {
  if (task.thread_id) {
    return `/workspace/chats/${task.thread_id}`;
  }
  return `/workspace/tasks/${task.id}`;
}

function TaskItem({
  task,
  isActive,
  onPauseResume,
  actionLoading,
  t,
}: {
  task: Task;
  isActive: boolean;
  onPauseResume: (task: Task) => void;
  actionLoading: string | null;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const hasThread = !!task.thread_id;
  const isTaskActive = task.status === "active";

  return (
    <SidebarMenuItem key={task.id} className="group/side-menu-item">
      <SidebarMenuButton isActive={isActive} asChild>
        <div>
          <Link
            className="text-muted-foreground block w-full whitespace-nowrap group-hover/side-menu-item:overflow-hidden"
            href={getTaskLink(task)}
          >
            <div className="flex items-center gap-2">
              {isTaskActive ? (
                <Play className="h-3 w-3 text-green-500" />
              ) : (
                <Pause className="h-3 w-3 text-orange-500" />
              )}
              <span className={`truncate ${!isTaskActive ? "opacity-60" : ""}`}>
                {task.name}
              </span>
              {hasThread && (
                <MessageCircle className="h-3 w-3 text-blue-500 flex-shrink-0" />
              )}
            </div>
          </Link>
          <div className="mt-1 flex items-center gap-2 pl-0.5">
            {isTaskActive ? (
              <Badge variant="outline" className="text-[10px]">
                <Clock className="mr-1 h-2.5 w-2.5" />
                {formatNextRun(task.next_run_at, t)}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px] opacity-60">
                <Pause className="mr-1 h-2.5 w-2.5" />
                {t.tasks.paused}
              </Badge>
            )}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <SidebarMenuAction
                showOnHover
                className="bg-background/50 hover:bg-background"
              >
                <MoreHorizontal />
                <span className="sr-only">{t.common.more}</span>
              </SidebarMenuAction>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="w-48 rounded-lg"
              side={"right"}
              align={"start"}
            >
              {hasThread && (
                <DropdownMenuItem asChild>
                  <Link href={`/workspace/chats/${task.thread_id}`}>
                    <MessageCircle className="text-muted-foreground" />
                    <span>{t.tasks.viewChat}</span>
                  </Link>
                </DropdownMenuItem>
              )}
              <DropdownMenuItem
                onSelect={() => onPauseResume(task)}
                disabled={actionLoading === task.id}
              >
                {isTaskActive ? (
                  <>
                    <Pause className="text-muted-foreground" />
                    <span>{t.tasks.pausedTask}</span>
                  </>
                ) : (
                  <>
                    <Play className="text-muted-foreground" />
                    <span>{t.tasks.resumeTask}</span>
                  </>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

export function ScheduledTasksList() {
  const { t } = useI18n();
  const pathname = usePathname();
  const { tasks, isLoading, refetch } = useScheduledTasks();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handlePauseResume = useCallback(
    async (task: Task) => {
      setActionLoading(task.id);
      try {
        if (task.status === "active") {
          await pauseTask(task.id);
          toast.success(t.tasks.taskPaused);
        } else {
          await resumeTask(task.id);
          toast.success(t.tasks.taskResumed);
        }
        void refetch();
      } catch {
        toast.error(t.tasks.operationFailed);
      } finally {
        setActionLoading(null);
      }
    },
    [refetch, t],
  );

  const activeTasks = tasks.filter((task) => task.status === "active");
  const pausedTasks = tasks.filter((task) => task.status === "paused");

  if (tasks.length === 0 && !isLoading) {
    return null;
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          {t.sidebar.automations}
        </div>
      </SidebarGroupLabel>
      <SidebarGroupContent className="group-data-[collapsible=icon]:pointer-events-none group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0">
        <SidebarMenu>
          <div className="flex w-full flex-col gap-1">
            {activeTasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                isActive={pathname === `/workspace/tasks/${task.id}` || pathname === `/workspace/chats/${task.thread_id}`}
                onPauseResume={handlePauseResume}
                actionLoading={actionLoading}
                t={t}
              />
            ))}

            {pausedTasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                isActive={pathname === `/workspace/tasks/${task.id}` || pathname === `/workspace/chats/${task.thread_id}`}
                onPauseResume={handlePauseResume}
                actionLoading={actionLoading}
                t={t}
              />
            ))}
          </div>
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
