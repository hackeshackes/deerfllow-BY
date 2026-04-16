import { redirect } from "next/navigation";

import { TokenUsageAdminPage } from "@/components/workspace/admin/token-usage-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminTokenUsagePage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <TokenUsageAdminPage />;
}
