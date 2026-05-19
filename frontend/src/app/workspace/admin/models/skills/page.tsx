import { redirect } from "next/navigation";

import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminModelsSkillsPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }
  redirect("/workspace/admin/skills");
}