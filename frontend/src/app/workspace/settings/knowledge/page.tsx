import { UserKnowledgePage } from "@/components/workspace/settings/user-knowledge-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceSettingsKnowledgePage() {
  await requireSession();
  return <UserKnowledgePage />;
}