import { redirect } from "next/navigation";

import { ConversationsAdminPage } from "@/components/workspace/admin/conversations-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminConversationsPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <ConversationsAdminPage />;
}
