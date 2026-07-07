"use client";

import { PlusIcon, WorkflowIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useWorkflows } from "@/core/canvas/hooks/use-workflows";
import { useI18n } from "@/core/i18n/hooks";
import { useCurrentSpace } from "@/core/spaces/hooks/use-current-space";

export default function WorkflowsListPage() {
  const { t } = useI18n();
  const { space } = useCurrentSpace();
  const workspaceId = space?.id ?? null;
  const { workflows, isLoading, error, refresh } = useWorkflows(workspaceId);

  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    setHydrated(true);
    document.title = `${t.canvasWorkflows.listTitle} - MicX`;
  }, [t]);

  const sorted = useMemo(
    () => [...workflows].sort((a, b) => b.updated_at.localeCompare(a.updated_at)),
    [workflows],
  );

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <Link href="/workspace/workflows/new">
          <Button size="sm" className="gap-2" data-testid="workflows-new">
            <PlusIcon className="size-4" />
            {t.canvasWorkflows.newWorkflow}
          </Button>
        </Link>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 py-8">
          <header>
            <h1 className="flex items-center gap-2 text-2xl font-semibold">
              <WorkflowIcon className="size-6" />
              {t.canvasWorkflows.listTitle}
            </h1>
            <p className="text-muted-foreground mt-2 text-sm">{t.canvasWorkflows.listDescription}</p>
          </header>

          {!hydrated || isLoading ? (
            <p className="text-muted-foreground text-center text-sm" data-testid="workflows-loading">
              {t.common.loading}
            </p>
          ) : error ? (
            <div
              role="alert"
              data-testid="workflows-error"
              className="text-destructive rounded border p-4 text-sm"
            >
              {t.canvasWorkflows.errorTitle}: {error.message}
              <Button size="sm" variant="outline" className="ml-2" onClick={() => void refresh()}>
                Retry
              </Button>
            </div>
          ) : sorted.length === 0 ? (
            <div
              className="rounded-2xl border py-12 text-center"
              data-testid="workflows-empty"
            >
              <WorkflowIcon className="text-muted-foreground mx-auto mb-3 size-10" />
              <p className="font-medium">{t.canvasWorkflows.emptyTitle}</p>
              <p className="text-muted-foreground text-sm">{t.canvasWorkflows.emptyDescription}</p>
              <Link href="/workspace/workflows/new" className="mt-4 inline-block">
                <Button size="sm">{t.canvasWorkflows.createButton}</Button>
              </Link>
            </div>
          ) : (
            <ul
              data-testid="workflows-grid"
              className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"
            >
              {sorted.map((wf) => (
                <li key={wf.id}>
                  <Card className="flex h-full flex-col" data-testid="workflow-card">
                    <CardHeader>
                      <CardTitle className="text-base">
                        <Link href={`/workspace/workflows/${wf.id}`} className="hover:underline">
                          {wf.name}
                        </Link>
                      </CardTitle>
                      <CardDescription className="line-clamp-2">
                        {wf.nodes.length} nodes · {wf.edges.length} edges
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="mt-auto flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-xs">
                        <Badge variant="secondary">{wf.status}</Badge>
                        <span className="text-muted-foreground">
                          {t.canvasWorkflows.versionLabel} {wf.version}
                        </span>
                      </div>
                      <div className="flex gap-1">
                        <Link href={`/workspace/workflows/${wf.id}/edit`}>
                          <Button size="sm" variant="outline" data-testid="workflow-edit">
                            {t.common.edit}
                          </Button>
                        </Link>
                      </div>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
