import { redirect } from "next/navigation";

import { MemoryAdminPage } from "@/components/workspace/admin/memory-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminMemoryPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <MemoryAdminPage />;
}