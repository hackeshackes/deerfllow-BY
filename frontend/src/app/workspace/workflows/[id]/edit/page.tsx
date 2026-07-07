"use client";

import { ChevronLeftIcon, SaveIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { canvasApi } from "@/core/canvas/api";
import { Canvas } from "@/core/canvas/components/Canvas";
import { EdgeConnector } from "@/core/canvas/components/EdgeConnector";
import { NodeInspector } from "@/core/canvas/components/NodeInspector";
import { NodePalette } from "@/core/canvas/components/NodePalette";
import type { CanvasEdge, CanvasNode, NodeKind } from "@/core/canvas/types";
import { useI18n } from "@/core/i18n/hooks";
import { useCurrentSpace } from "@/core/spaces/hooks/use-current-space";

import { WorkflowToolbar } from "./components/WorkflowToolbar";

let nodeSeq = 0;
function nextNodeId(kind: NodeKind): string {
  nodeSeq += 1;
  return `n-${kind}-${Date.now().toString(36)}-${nodeSeq}`;
}

let edgeSeq = 0;
function nextEdgeId(): string {
  edgeSeq += 1;
  return `e-${Date.now().toString(36)}-${edgeSeq}`;
}

export default function EditWorkflowPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const { space } = useCurrentSpace();

  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const [edges, setEdges] = useState<CanvasEdge[]>([]);
  const [name, setName] = useState("");
  const [version, setVersion] = useState(1);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Load workflow on mount.
  useEffect(() => {
    if (!params?.id) return;
    let cancelled = false;
    canvasApi
      .get(params.id)
      .then((wf) => {
        if (cancelled) return;
        setNodes(wf.nodes);
        setEdges(wf.edges);
        setName(wf.name);
        setVersion(wf.version);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [params?.id]);

  useEffect(() => {
    if (name) document.title = `${t.canvasWorkflows.editTitle}: ${name} - MicX`;
  }, [t, name]);

  const onAddNode = useCallback((kind: NodeKind) => {
    setNodes((prev) => [
      ...prev,
      {
        id: nextNodeId(kind),
        kind,
        config: {},
        position: [40 + (prev.length % 4) * 220, 40 + Math.floor(prev.length / 4) * 140],
      },
    ]);
  }, []);

  const onCreateEdge = useCallback((edge: Omit<CanvasEdge, "id">) => {
    setEdges((prev) => [...prev, { ...edge, id: nextEdgeId() }]);
  }, []);

  const onUpdateNode = useCallback((id: string, patch: Partial<CanvasNode>) => {
    setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, ...patch } : n)));
  }, []);

  const onRemoveNode = useCallback(
    (id: string) => {
      setNodes((prev) => prev.filter((n) => n.id !== id));
      setEdges((prev) => prev.filter((e) => e.source_node_id !== id && e.target_node_id !== id));
      setSelectedNodeId((cur) => (cur === id ? null : cur));
    },
    [],
  );

  const onSave = useCallback(async () => {
    if (!params?.id) return;
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await canvasApi.update(params.id, {
        name,
        nodes,
        edges,
      });
      setSavedAt(new Date(updated.updated_at).toLocaleTimeString());
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }, [params?.id, name, nodes, edges]);

  const refreshAfterRollback = useCallback(async () => {
    if (!params?.id) return;
    try {
      const wf = await canvasApi.get(params.id);
      setNodes(wf.nodes);
      setEdges(wf.edges);
      setName(wf.name);
      setVersion(wf.version);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    }
  }, [params?.id]);

  if (loadError) {
    return (
      <WorkspaceContainer>
        <WorkspaceBody>
          <p role="alert" className="text-destructive" data-testid="workflow-edit-error">
            {loadError}
          </p>
          <Link href="/workspace/workflows" className="mt-2 inline-block">
            <Button variant="outline">{t.canvasWorkflows.backToList}</Button>
          </Link>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  if (!name && nodes.length === 0) {
    return (
      <WorkspaceContainer>
        <WorkspaceBody>
          <p className="text-muted-foreground" data-testid="workflow-edit-loading">
            {t.common.loading}
          </p>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <div className="flex items-center gap-2">
          <Link href={`/workspace/workflows/${params?.id ?? ""}`}>
            <Button size="sm" variant="outline">
              <ChevronLeftIcon className="size-4" />
              {t.canvasWorkflows.backToList}
            </Button>
          </Link>
          <h1 className="text-lg font-semibold" data-testid="workflow-edit-name">
            {name || t.canvasWorkflows.editTitle}
          </h1>
          {savedAt && (
            <span className="text-muted-foreground text-xs" data-testid="workflow-edit-saved">
              {t.canvasWorkflows.savedAt.replace("{time}", savedAt)}
            </span>
          )}
          {saveError && (
            <span role="alert" className="text-destructive text-xs" data-testid="workflow-edit-save-error">
              {saveError}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{space?.name ?? space?.id ?? "—"}</Badge>
          <WorkflowToolbar
            workflowId={params?.id ?? null}
            currentVersion={version}
            onRollback={() => void refreshAfterRollback()}
          />
          <Button
            size="sm"
            onClick={onSave}
            disabled={saving}
            data-testid="workflow-edit-save"
          >
            <SaveIcon className="size-4" />
            {saving ? t.canvasWorkflows.savingChanges : t.canvasWorkflows.saveChanges}
          </Button>
        </div>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="flex h-full flex-col">
          <NodePalette onAdd={onAddNode} disabled={saving} />
          <EdgeConnector nodes={nodes} onCreate={onCreateEdge} />
          <div className="flex flex-1 flex-col gap-3 lg:flex-row">
            <Canvas
              nodes={nodes}
              edges={edges}
              onNodesChange={setNodes}
              onEdgesChange={setEdges}
              onSelectNode={setSelectedNodeId}
              selectedNodeId={selectedNodeId}
            />
            <NodeInspector
              node={selectedNode}
              edges={edges}
              onUpdate={onUpdateNode}
              onRemove={onRemoveNode}
            />
          </div>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
