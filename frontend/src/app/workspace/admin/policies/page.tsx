import { redirect } from "next/navigation";

import { AbacPoliciesPage } from "@/components/workspace/admin/abac-policies-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminPoliciesPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <AbacPoliciesPage />;
}