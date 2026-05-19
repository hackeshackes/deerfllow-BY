import { redirect } from "next/navigation";

import { VoiceAdminPage } from "@/components/workspace/admin/voice-admin-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAdminVoicePage() {
  const session = await requireSession();
  if (session.role !== "owner") {
    redirect("/workspace");
  }

  return <VoiceAdminPage />;
}