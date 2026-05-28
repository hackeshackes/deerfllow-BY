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
import { useI18n } from "@/core/i18n/hooks";
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
  const { t } = useI18n();
  const { skills, isLoading, error } = useUserSkills();

  useEffect(() => {
    document.title = `${t.sidebar.workflows} - MicX`;
  }, [t.sidebar.workflows]);

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
            {t.settings.skills.advancedManagement}
          </Button>
        </Link>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 py-8">
          <div>
            <div className="flex items-center gap-2 text-2xl font-semibold">
              <WorkflowIcon className="size-6" />
              {t.sidebar.workflows}
            </div>
            <p className="text-muted-foreground mt-2 text-sm">
              {t.workflows.description}
            </p>
          </div>

          {isLoading ? (
            <div className="text-muted-foreground text-center">{t.common.loading}</div>
          ) : error ? (
            <div className="text-destructive text-sm">{t.workflows.loadError}: {error.message}</div>
          ) : (
            <Tabs defaultValue="enabled">
              <TabsList>
                <TabsTrigger value="enabled">{t.workflows.availableWorkflows}</TabsTrigger>
                <TabsTrigger value="defaults">{t.workflows.defaultWorkflows}</TabsTrigger>
                <TabsTrigger value="all">{t.workflows.all}</TabsTrigger>
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
  const { t } = useI18n();

  if (skills.length === 0) {
    return (
      <div className="rounded-2xl border py-12 text-center">
        <WorkflowIcon className="text-muted-foreground mx-auto mb-3 size-10" />
        <p className="text-muted-foreground">{t.workflows.noWorkflows}</p>
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
                {skill.description || t.workflows.noWorkflows}
                </CardDescription>
              </div>
              {skill.is_default && (
                <Badge variant="secondary" className="gap-1">
                  <StarIcon className="size-3" />
                  {t.workflows.defaultWorkflows}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="mt-auto space-y-4">
            <div className="text-muted-foreground flex items-center justify-between text-sm">
              <span>{skill.enabled ? t.workflows.enabled : t.workflows.disabled}</span>
              {skill.average_rating !== null && <span>{t.workflows.rating} {skill.average_rating.toFixed(1)}</span>}
            </div>
            <div className="flex gap-2">
              <Button asChild size="sm" className="flex-1 gap-1">
                <Link href={workflowHref(skill)}>
                  <PlayIcon className="size-4" />
                  {t.workflows.use}
                </Link>
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="flex-1 gap-1"
                onClick={() => onCreateAutomation(skill)}
              >
                <ClockIcon className="size-4" />
                {t.workflows.automation}
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
