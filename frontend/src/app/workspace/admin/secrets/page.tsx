import { redirect } from "next/navigation";

import { SecretsAdminPage } from "@/components/workspace/admin/secrets-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminSecretsPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <SecretsAdminPage />;
}