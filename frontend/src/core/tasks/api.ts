import { getBackendBaseURL } from "@/core/config";

export interface TriggerConfig {
  cron?: string;
  interval_seconds?: number;
  interval_minutes?: number;
  interval_hours?: number;
  interval_days?: number;
  timezone: string;
  start_date?: string;
  end_date?: string;
}

export interface NotificationConfig {
  enabled: boolean;
  channels: string[];
}

export interface OutputConfig {
  save_to_thread: boolean;
  webhook_url?: string;
}

export interface Task {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  trigger_type: string;
  trigger_config: TriggerConfig;
  prompt_template: string;
  model_name?: string;
  skill_names: string[];
  notification_config: NotificationConfig;
  output_config: OutputConfig;
  status: string;
  next_run_at?: string;
  last_run_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TaskExecution {
  id: string;
  task_id: string;
  thread_id?: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  result_summary?: string;
  error_message?: string;
  token_used: number;
}

export interface CreateTaskRequest {
  name: string;
  description?: string;
  trigger_type: string;
  trigger_config: TriggerConfig;
  prompt_template: string;
  model_name?: string;
  skill_names?: string[];
  notification_config?: NotificationConfig;
  output_config?: OutputConfig;
}

export interface UpdateTaskRequest {
  name?: string;
  description?: string;
  trigger_type?: string;
  trigger_config?: TriggerConfig;
  prompt_template?: string;
  model_name?: string;
  skill_names?: string[];
  notification_config?: NotificationConfig;
  output_config?: OutputConfig;
  status?: string;
}

export async function loadTasks(): Promise<Task[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks`);
  return response.json();
}

export async function getTask(taskId: string): Promise<Task> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks/${taskId}`);
  return response.json();
}

export async function createTask(request: CreateTaskRequest): Promise<Task> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? `HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function updateTask(taskId: string, request: UpdateTaskRequest): Promise<Task> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks/${taskId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? `HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function deleteTask(taskId: string): Promise<{ success: boolean }> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks/${taskId}`, {
    method: "DELETE",
  });
  return response.json();
}

export async function runTaskNow(taskId: string): Promise<TaskExecution> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks/${taskId}/run`, {
    method: "POST",
  });
  return response.json();
}

export async function pauseTask(taskId: string): Promise<Task> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks/${taskId}/pause`, {
    method: "POST",
  });
  return response.json();
}

export async function resumeTask(taskId: string): Promise<Task> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks/${taskId}/resume`, {
    method: "POST",
  });
  return response.json();
}

export async function getTaskExecutions(taskId: string): Promise<TaskExecution[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/tasks/${taskId}/executions`);
  return response.json();
}
