import { redirect } from "next/navigation";

import { MonitoringAdminPage } from "@/components/workspace/admin/monitoring-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminMonitoringPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <MonitoringAdminPage />;
}
