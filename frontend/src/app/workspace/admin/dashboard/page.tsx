import { redirect } from "next/navigation";

import { DashboardAdminPage } from "@/components/workspace/admin/dashboard-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminDashboardPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <DashboardAdminPage />;
}
