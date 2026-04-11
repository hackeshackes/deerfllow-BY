import { redirect } from "next/navigation";

import { ModelsAdminPage } from "@/components/workspace/admin/models-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminModelsPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <ModelsAdminPage />;
}
