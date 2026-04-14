import { redirect } from "next/navigation";

import { SkillsAdminPage } from "@/components/workspace/admin/skills-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminSkillsPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <SkillsAdminPage />;
}
