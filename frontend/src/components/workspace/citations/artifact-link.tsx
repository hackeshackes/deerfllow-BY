import type { AnchorHTMLAttributes } from "react";
import { createContext, useContext } from "react";

import { urlOfArtifact } from "@/core/artifacts/utils";
import { cn } from "@/lib/utils";

import { CitationLink } from "./citation-link";

const ArtifactLinkContext = createContext<{ threadId: string } | null>(null);

export function useArtifactLinkContext() {
  return useContext(ArtifactLinkContext);
}

export function ArtifactLinkContextProvider({
  threadId,
  children,
}: {
  threadId: string;
  children: React.ReactNode;
}) {
  return (
    <ArtifactLinkContext.Provider value={{ threadId }}>
      {children}
    </ArtifactLinkContext.Provider>
  );
}

function isExternalUrl(href: string | undefined): boolean {
  return !!href && /^https?:\/\//.test(href);
}

export function ArtifactLink(props: AnchorHTMLAttributes<HTMLAnchorElement>) {
  if (typeof props.children === "string") {
    const match = /^citation:(.+)$/.exec(props.children);
    if (match) {
      const [, text] = match;
      return <CitationLink {...props}>{text}</CitationLink>;
    }
  }
  const { className, target, rel, href, ...rest } = props;
  const external = isExternalUrl(href);
  const context = useContext(ArtifactLinkContext);

  let resolvedHref = href;
  if (href && href.startsWith("/mnt/") && context) {
    resolvedHref = urlOfArtifact({
      filepath: href,
      threadId: context.threadId,
      download: true,
    });
  }

  return (
    <a
      {...rest}
      href={resolvedHref}
      className={cn(
        "text-primary decoration-primary/30 hover:decoration-primary/60 underline underline-offset-2 transition-colors",
        className,
      )}
      target={target ?? (external ? "_blank" : undefined)}
      rel={rel ?? (external ? "noopener noreferrer" : undefined)}
    />
  );
}
