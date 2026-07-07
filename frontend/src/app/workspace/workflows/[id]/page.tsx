"use client";

import { ChevronLeftIcon, PlayIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { canvasApi } from "@/core/canvas/api";
import { Canvas } from "@/core/canvas/components/Canvas";
import { NodeInspector } from "@/core/canvas/components/NodeInspector";
import { useWorkflowExecute } from "@/core/canvas/hooks/use-workflow-execute";
import type { ExecutionResult, Workflow } from "@/core/canvas/types";
import { useI18n } from "@/core/i18n/hooks";
import { useCurrentSpace } from "@/core/spaces/hooks/use-current-space";

export default function WorkflowDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const { space } = useCurrentSpace();
  const { run, isRunning, result, error: runError, reset } = useWorkflowExecute();

  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [inputsText, setInputsText] = useState("{}");
  const [inputsParseError, setInputsParseError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!params?.id) return;
    canvasApi
      .get(params.id)
      .then((wf) => {
        if (!cancelled) setWorkflow(wf);
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [params?.id]);

  useEffect(() => {
    if (workflow) document.title = `${workflow.name} - MicX`;
  }, [workflow]);

  const onRun = useCallback(async () => {
    if (!workflow || !space) return;
    let parsed: Record<string, unknown> = {};
    try {
      parsed = JSON.parse(inputsText) as Record<string, unknown>;
      setInputsParseError(null);
    } catch (err) {
      setInputsParseError(err instanceof Error ? err.message : String(err));
      return;
    }
    reset();
    await run(workflow.id, { inputs: parsed, workspace_id: space.id });
  }, [workflow, space, inputsText, run, reset]);

  if (loadError) {
    return (
      <WorkspaceContainer>
        <WorkspaceBody>
          <p role="alert" className="text-destructive" data-testid="workflow-detail-error">
            {loadError}
          </p>
          <Link href="/workspace/workflows" className="mt-2 inline-block">
            <Button variant="outline">{t.canvasWorkflows.backToList}</Button>
          </Link>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  if (!workflow) {
    return (
      <WorkspaceContainer>
        <WorkspaceBody>
          <p className="text-muted-foreground" data-testid="workflow-loading">
            {t.common.loading}
          </p>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  const selectedNode = workflow.nodes.find((n) => n.id === selectedNodeId) ?? null;

  // Read-only stubs so the Canvas component does not mutate state.
  const noop = () => {
    // intentional no-op
  };

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <div className="flex items-center gap-2">
          <Link href="/workspace/workflows">
            <Button size="sm" variant="outline">
              <ChevronLeftIcon className="size-4" />
              {t.canvasWorkflows.backToList}
            </Button>
          </Link>
          <h1 className="text-lg font-semibold" data-testid="workflow-detail-name">
            {workflow.name}
          </h1>
          <Badge variant="secondary">{workflow.status}</Badge>
          <span className="text-muted-foreground text-xs">
            {t.canvasWorkflows.versionLabel} {workflow.version}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Link href={`/workspace/workflows/${workflow.id}/edit`}>
            <Button size="sm" variant="outline" data-testid="workflow-detail-edit">
              {t.common.edit}
            </Button>
          </Link>
          <Button
            size="sm"
            onClick={onRun}
            disabled={isRunning || !space}
            data-testid="workflow-detail-run"
          >
            <PlayIcon className="size-4" />
            {isRunning ? t.canvasWorkflows.running : t.canvasWorkflows.run}
          </Button>
        </div>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="flex h-full flex-col gap-3 lg:flex-row">
          <div className="flex flex-1 flex-col">
            <Canvas
              nodes={workflow.nodes}
              edges={workflow.edges}
              onNodesChange={noop}
              onEdgesChange={noop}
              onSelectNode={setSelectedNodeId}
              selectedNodeId={selectedNodeId}
            />
          </div>
          <div className="flex w-full flex-col gap-3 lg:w-96">
            <NodeInspector
              node={selectedNode}
              edges={workflow.edges}
              onUpdate={noop}
              onRemove={noop}
            />
            <section className="rounded-2xl border p-4 text-sm" data-testid="workflow-run-panel">
              <h3 className="mb-2 font-semibold">{t.canvasWorkflows.runInputs}</h3>
              <Textarea
                data-testid="workflow-run-inputs"
                value={inputsText}
                onChange={(e) => setInputsText(e.target.value)}
                className="h-24 font-mono text-xs"
              />
              {inputsParseError && (
                <p role="alert" className="text-destructive mt-1 text-xs">
                  {inputsParseError}
                </p>
              )}
              {runError && (
                <p
                  role="alert"
                  className="text-destructive mt-1 text-xs"
                  data-testid="workflow-run-error"
                >
                  {runError.message.startsWith("canvas API 429")
                    ? t.canvasWorkflows.quotaExceeded
                    : `${t.canvasWorkflows.runError}: ${runError.message}`}
                </p>
              )}
              {result && <ResultPanel result={result} />}
            </section>
          </div>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}

function ResultPanel({ result }: { result: ExecutionResult }) {
  const failed = result.steps.filter((s) => s.status === "failed");
  return (
    <div className="mt-3 space-y-2" data-testid="workflow-run-result">
      <h3 className="font-semibold">Result</h3>
      {failed.length > 0 && (
        <p className="text-destructive text-xs">
          {failed.length} step(s) failed
        </p>
      )}
      <ul className="space-y-1 text-xs">
        {result.steps.map((s) => (
          <li
            key={s.node_id}
            data-testid="run-step"
            data-step-status={s.status}
            className="rounded border bg-gray-50 px-2 py-1"
          >
            <code>{s.node_id}</code> · {s.status}
            {s.error && <span className="text-destructive ml-1">— {s.error}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
