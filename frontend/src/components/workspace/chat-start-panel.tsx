"use client";

import {
  FileTextIcon,
  LightbulbIcon,
  RepeatIcon,
  SearchIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";
import { loadKnowledgeBases, type KnowledgeBase } from "@/core/knowledge";
import { useUserSkills } from "@/core/skills/hooks";

type CurrentUser = {
  active_workspace_name?: string | null;
};

function promptHref(prompt: string): string {
  const params = new URLSearchParams({ prompt });
  return `/workspace/chats/new?${params.toString()}`;
}

export function ChatStartPanel() {
  const { t } = useI18n();
  const { skills } = useUserSkills();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    Promise.all([
      loadKnowledgeBases(),
      fetch("/api/users/me").then((response) => response.json()),
    ])
      .then(([kbs, user]) => {
        setKnowledgeBases(kbs.slice(0, 4));
        setCurrentUser(user as CurrentUser);
      })
      .catch(() => {
        // The start panel should never block plain chat.
      });
  }, []);

  const enabledSkills = skills.filter((skill) => skill.enabled).slice(0, 4);

  const quickActions = [
    {
      title: t.chatStartPanel.basedOnKnowledge,
      description: t.chatStartPanel.knowledgeDescription,
      icon: SearchIcon,
      prompt: "请基于当前空间的资料库回答我的问题：",
    },
    {
      title: t.chatStartPanel.writeDocument,
      description: t.chatStartPanel.writeDocumentDescription,
      icon: FileTextIcon,
      prompt: "请帮我撰写一份文档，主题是：",
    },
    {
      title: t.chatStartPanel.analyzeProblem,
      description: t.chatStartPanel.analyzeProblemDescription,
      icon: LightbulbIcon,
      prompt: "请帮我分析这个问题，并给出可执行建议：",
    },
    {
      title: t.chatStartPanel.createAutomation,
      description: t.chatStartPanel.createAutomationDescription,
      icon: RepeatIcon,
      prompt: "我想创建一个自动化，定期帮我完成：",
    },
  ];

  return (
    <div className="mx-auto flex w-full flex-col gap-3 px-2 pb-2 pt-3">
      {/* Current space + quick actions — single horizontal strip */}
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border bg-card p-3">
        <span className="shrink-0 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
          {currentUser?.active_workspace_name ?? t.chatStartPanel.micXWorkspace}
        </span>
        <div className="flex flex-wrap gap-1.5">
          {quickActions.map((action) => (
            <Link key={action.title} href={promptHref(action.prompt)}>
              <div className="hover:bg-muted/60 flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-left text-xs transition-colors">
                <action.icon className="text-muted-foreground size-3" />
                <span className="whitespace-nowrap font-medium">{action.title}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
      {(knowledgeBases.length > 0 || enabledSkills.length > 0) && (
        <div className="flex flex-wrap items-center gap-2 rounded-2xl border bg-card p-3">
          {knowledgeBases.length > 0 && (
            <>
              <span className="text-muted-foreground shrink-0 text-xs font-medium">{t.chatStartPanel.knowledgeBase}</span>
              <div className="flex flex-wrap gap-1">
                {knowledgeBases.map((kb) => (
                  <Link key={kb.id} href={promptHref(`请参考「${kb.name}」资料库，帮我：`)}>
                    <Button size="sm" variant="outline" className="text-xs">{kb.name}</Button>
                  </Link>
                ))}
              </div>
            </>
          )}
          {enabledSkills.length > 0 && (
            <>
              <span className="text-muted-foreground shrink-0 text-xs font-medium">{t.chatStartPanel.workflow}</span>
              <div className="flex flex-wrap gap-1">
                {enabledSkills.map((skill) => (
                  <Link key={skill.skill_name} href={promptHref(`请使用「${skill.display_name}」工作流，帮我：`)}>
                    <Button size="sm" variant="outline" className="text-xs">{skill.display_name}</Button>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
