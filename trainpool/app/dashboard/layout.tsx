import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { SignOutButton } from "./sign-out-button";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen">
      <nav className="border-b border-ink-200 bg-ink-50/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <Link href="/dashboard" className="font-display text-xl font-semibold text-ink-800">
            TrainPool
          </Link>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-ink-500 sm:inline">{user.email}</span>
            <SignOutButton />
          </div>
        </div>
      </nav>
      {children}
    </div>
  );
}
