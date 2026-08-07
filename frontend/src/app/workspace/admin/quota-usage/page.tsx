import { redirect } from "next/navigation";

import { QuotaUsagePage } from "@/components/workspace/admin/quota-usage-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminQuotaUsagePage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <QuotaUsagePage />;
}