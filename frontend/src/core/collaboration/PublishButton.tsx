"use client";

import * as React from "react";

import { listWorkspaces, publishThread, type Workspace } from "./api";

type Status = "idle" | "loading" | "ok" | "err";

type Props = {
  threadId: string;
  currentWorkspaceId: string;
};

/**
 * PublishButton — cross-workspace publish of the current thread.
 *
 * On mount it fetches the workspace list once to decide whether the button is
 * even useful: if there are no OTHER workspaces to publish into (nothing but
 * the current one), the button is hidden entirely — a single-workspace or
 * personal deployment gets no empty dead-end dialog.
 *
 * When shown, opening the dialog reuses the already-fetched list (no second
 * fetch); the user picks a target and we POST /api/threads/{id}/publish.
 */
export function PublishButton({ threadId, currentWorkspaceId }: Props) {
  const [open, setOpen] = React.useState(false);
  const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
  const [loaded, setLoaded] = React.useState(false);
  const [target, setTarget] = React.useState("");
  const [status, setStatus] = React.useState<Status>("idle");
  const submittingRef = React.useRef(false);

  React.useEffect(() => {
    let cancelled = false;
    listWorkspaces()
      .then((ws) => {
        if (cancelled) return;
        setWorkspaces(ws);
        setLoaded(true);
      })
      .catch(() => {
        if (cancelled) return;
        // Dereference on error: hide the button rather than show a broken
        // feature the user can't act on.
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const targets = workspaces.filter((w) => w.id !== currentWorkspaceId);

  // Wait for the workspace prefetch; avoid a flash of the button that then
  // disappears once we know there is nowhere to publish to.
  if (!loaded) {
    return null;
  }
  if (targets.length === 0) {
    // Only the current workspace exists — publishing is a no-op here.
    return null;
  }

  const submit = async () => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setStatus("loading");
    try {
      await publishThread(threadId, target);
      setStatus("ok");
    } catch {
      setStatus("err");
    } finally {
      submittingRef.current = false;
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
            {targets.map((w) => (
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