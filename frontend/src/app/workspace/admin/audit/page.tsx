import { redirect } from "next/navigation";

import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminAuditPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }
  redirect("/workspace/admin/monitoring");
}