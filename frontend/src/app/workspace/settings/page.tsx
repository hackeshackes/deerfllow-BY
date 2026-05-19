import { redirect } from "next/navigation";

import { requireSession } from "@/server/auth/session";

export default async function WorkspaceSettingsPage() {
  const session = await requireSession();
  // Redirect to account page as default settings view
  redirect("/workspace/account");
}