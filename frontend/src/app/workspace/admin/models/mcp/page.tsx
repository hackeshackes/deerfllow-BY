import { redirect } from "next/navigation";

import { MCPAdminPage } from "@/components/workspace/admin/mcp-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminMCPPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <MCPAdminPage />;
}
