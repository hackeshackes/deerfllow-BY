import { redirect } from "next/navigation";

import { KnowledgeAdminPage } from "@/components/workspace/admin/knowledge-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminKnowledgePage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <KnowledgeAdminPage />;
}
