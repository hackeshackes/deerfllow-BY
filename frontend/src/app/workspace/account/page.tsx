import { AccountPage } from "@/components/workspace/account/account-page";
import { requireSession } from "@/server/auth/session";

export default async function WorkspaceAccountPage() {
  await requireSession();
  return <AccountPage />;
}
