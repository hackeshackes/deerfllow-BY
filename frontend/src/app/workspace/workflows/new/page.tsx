"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useWorkflows } from "@/core/canvas/hooks/use-workflows";
import { useI18n } from "@/core/i18n/hooks";
import { useCurrentSpace } from "@/core/spaces/hooks/use-current-space";

export default function NewWorkflowPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { space } = useCurrentSpace();
  const { create } = useWorkflows(space?.id ?? null);

  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = `${t.canvasWorkflows.createTitle} - MicX`;
  }, [t]);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!name.trim() || !space) return;
    setSubmitting(true);
    setError(null);
    try {
      const wf = await create({ name: name.trim(), workspace_id: space.id });
      router.push(`/workspace/workflows/${wf.id}/edit`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <Link href="/workspace/workflows">
          <Button size="sm" variant="outline">
            {t.canvasWorkflows.backToList}
          </Button>
        </Link>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="mx-auto w-full max-w-xl py-8">
          <header className="mb-6">
            <h1 className="text-2xl font-semibold">{t.canvasWorkflows.createTitle}</h1>
            <p className="text-muted-foreground mt-2 text-sm">{t.canvasWorkflows.createDescription}</p>
          </header>

          <form
            onSubmit={submit}
            data-testid="workflow-new-form"
            className="space-y-4 rounded-2xl border p-6"
          >
            <div>
              <label htmlFor="workflow-name" className="text-sm font-medium">
                {t.canvasWorkflows.nameLabel}
              </label>
              <Input
                id="workflow-name"
                data-testid="workflow-name-input"
                placeholder={t.canvasWorkflows.namePlaceholder}
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={submitting}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t.canvasWorkflows.workspaceLabel}</label>
              <p className="mt-1 rounded border bg-gray-50 p-2 text-sm" data-testid="workflow-workspace">
                {space?.name ?? space?.id ?? "—"}
              </p>
            </div>
            {error && (
              <p role="alert" className="text-destructive text-sm" data-testid="workflow-new-error">
                {t.canvasWorkflows.createError}: {error}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Link href="/workspace/workflows">
                <Button type="button" variant="outline" disabled={submitting}>
                  {t.canvasWorkflows.createCancel}
                </Button>
              </Link>
              <Button
                type="submit"
                data-testid="workflow-new-submit"
                disabled={!name.trim() || !space || submitting}
              >
                {t.canvasWorkflows.createSubmit}
              </Button>
            </div>
          </form>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
