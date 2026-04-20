import { redirect } from "next/navigation";

import { ChannelsAdminPage } from "@/components/workspace/admin/channels-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminChannelsPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <ChannelsAdminPage />;
}
