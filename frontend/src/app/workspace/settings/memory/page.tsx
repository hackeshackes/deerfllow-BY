import { redirect } from "next/navigation";

import { MemorySettingsPage } from "@/components/workspace/settings/memory-settings-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceSettingsMemoryPage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <MemorySettingsPage />;
}
