import { redirect } from "next/navigation";

import { ConnectorsAdminPage } from "@/components/workspace/admin/connectors-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminConnectorsPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }
  return <ConnectorsAdminPage />;
}
