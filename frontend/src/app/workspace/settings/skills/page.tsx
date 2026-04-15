import { UserSkillsPage } from "@/components/workspace/settings/user-skills-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceSettingsSkillsPage() {
  await requireSession();
  return <UserSkillsPage />;
}