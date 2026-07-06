"use client";

import * as React from "react";

import { listWorkspaces, publishThread, type Workspace } from "./api";

type Status = "idle" | "loading" | "ok" | "err";

type Props = {
  threadId: string;
  currentWorkspaceId: string;
};

/**
 * PublishButton — opens a dialog that prompts the user to pick a target
 * workspace, then POSTs to /api/threads/{threadId}/publish with the
 * selection. Filters out the current workspace from the list.
 */
export function PublishButton({ threadId, currentWorkspaceId }: Props) {
  const [open, setOpen] = React.useState(false);
  const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
  const [target, setTarget] = React.useState("");
  const [status, setStatus] = React.useState<Status>("idle");

  React.useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setStatus("loading");
    listWorkspaces()
      .then((ws) => {
        if (cancelled) return;
        setWorkspaces(ws.filter((w) => w.id !== currentWorkspaceId));
        setStatus("idle");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("err");
      });
    return () => {
      cancelled = true;
    };
  }, [open, currentWorkspaceId]);

  const submit = async () => {
    setStatus("loading");
    try {
      await publishThread(threadId, target);
      setStatus("ok");
    } catch {
      setStatus("err");
    }
  };

  const close = () => {
    setOpen(false);
    setTarget("");
    setStatus("idle");
  };

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-label="publish">
        Publish
      </button>
      {open ? (
        <div role="dialog" aria-label="publish-thread">
          <select
            aria-label="target-workspace"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
          >
            <option value="">Select workspace</option>
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={submit}
            disabled={!target || status === "loading"}
          >
            Confirm
          </button>
          <button type="button" onClick={close} aria-label="close-dialog">
            Close
          </button>
          {status === "ok" ? <span role="status">Published</span> : null}
          {status === "err" ? <span role="alert">Failed</span> : null}
        </div>
      ) : null}
    </>
  );
}
