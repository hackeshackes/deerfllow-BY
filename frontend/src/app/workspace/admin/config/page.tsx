import { redirect } from "next/navigation";

import { ConfigAdminPage } from "@/components/workspace/admin/config-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminConfigPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <ConfigAdminPage />;
}
