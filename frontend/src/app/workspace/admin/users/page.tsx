import { redirect } from "next/navigation";

import { UsersAdminPage } from "@/components/workspace/admin/users-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceUsersAdminPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <UsersAdminPage />;
}
