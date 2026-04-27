"use client";

import { ClockIcon, PlayIcon, SettingsIcon, StarIcon, WorkflowIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useUserSkills } from "@/core/skills/hooks";
import type { UserSkillConfig } from "@/core/skills/type";

function workflowPrompt(skill: UserSkillConfig): string {
  return `请使用「${skill.display_name}」工作流来完成任务。\n\n我的目标是：`;
}

function workflowHref(skill: UserSkillConfig): string {
  const params = new URLSearchParams({
    workflow: skill.skill_name,
    prompt: workflowPrompt(skill),
  });
  return `/workspace/chats/new?${params.toString()}`;
}

export default function WorkflowsPage() {
  const router = useRouter();
  const { skills, isLoading, error } = useUserSkills();

  useEffect(() => {
    document.title = "工作流 - MicX";
  }, []);

  const enabledSkills = useMemo(
    () => skills.filter((skill) => skill.enabled),
    [skills],
  );
  const defaultSkills = useMemo(
    () => skills.filter((skill) => skill.is_default),
    [skills],
  );

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <Link href="/workspace/settings/skills">
          <Button size="sm" variant="outline" className="gap-2">
            <SettingsIcon className="size-4" />
            高级管理
          </Button>
        </Link>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 py-8">
          <div>
            <div className="flex items-center gap-2 text-2xl font-semibold">
              <WorkflowIcon className="size-6" />
              工作流
            </div>
            <p className="text-muted-foreground mt-2 text-sm">
              把技能包装成可直接使用的任务模板。你可以从这里开始对话，或创建周期性自动化。
            </p>
          </div>

          {isLoading ? (
            <div className="text-muted-foreground text-center">加载中...</div>
          ) : error ? (
            <div className="text-destructive text-sm">加载工作流失败：{error.message}</div>
          ) : (
            <Tabs defaultValue="enabled">
              <TabsList>
                <TabsTrigger value="enabled">可用工作流</TabsTrigger>
                <TabsTrigger value="defaults">常用</TabsTrigger>
                <TabsTrigger value="all">全部</TabsTrigger>
              </TabsList>
              <TabsContent value="enabled" className="mt-4">
                <WorkflowGrid skills={enabledSkills} onCreateAutomation={(skill) => router.push(`/workspace/automations/new?workflow=${encodeURIComponent(skill.skill_name)}`)} />
              </TabsContent>
              <TabsContent value="defaults" className="mt-4">
                <WorkflowGrid skills={defaultSkills} onCreateAutomation={(skill) => router.push(`/workspace/automations/new?workflow=${encodeURIComponent(skill.skill_name)}`)} />
              </TabsContent>
              <TabsContent value="all" className="mt-4">
                <WorkflowGrid skills={skills} onCreateAutomation={(skill) => router.push(`/workspace/automations/new?workflow=${encodeURIComponent(skill.skill_name)}`)} />
              </TabsContent>
            </Tabs>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}

function WorkflowGrid({
  skills,
  onCreateAutomation,
}: {
  skills: UserSkillConfig[];
  onCreateAutomation: (skill: UserSkillConfig) => void;
}) {
  if (skills.length === 0) {
    return (
      <div className="rounded-2xl border py-12 text-center">
        <WorkflowIcon className="text-muted-foreground mx-auto mb-3 size-10" />
        <p className="text-muted-foreground">暂无可用工作流。</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {skills.map((skill) => (
        <Card key={skill.skill_name} className="flex flex-col">
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="text-base">{skill.display_name}</CardTitle>
                <CardDescription className="mt-2 line-clamp-3">
                  {skill.description || "团队可复用的 AI 工作流程。"}
                </CardDescription>
              </div>
              {skill.is_default && (
                <Badge variant="secondary" className="gap-1">
                  <StarIcon className="size-3" />
                  常用
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="mt-auto space-y-4">
            <div className="text-muted-foreground flex items-center justify-between text-sm">
              <span>{skill.enabled ? "已启用" : "未启用"}</span>
              {skill.average_rating !== null && <span>评分 {skill.average_rating.toFixed(1)}</span>}
            </div>
            <div className="flex gap-2">
              <Button asChild size="sm" className="flex-1 gap-1">
                <Link href={workflowHref(skill)}>
                  <PlayIcon className="size-4" />
                  使用
                </Link>
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="flex-1 gap-1"
                onClick={() => onCreateAutomation(skill)}
              >
                <ClockIcon className="size-4" />
                自动化
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
