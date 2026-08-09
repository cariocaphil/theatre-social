"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth-provider";

/** Minimal authenticated account summary for `/me`. Not a public profile. */
export function AccountSummary() {
  const { status, user } = useAuth();

  if (status === "loading") {
    return <p role="status">Loading account…</p>;
  }

  if (status !== "authenticated" || !user) {
    return (
      <div role="alert">
        <p>You need to be logged in to view this page.</p>
        <p>
          <Link href="/login">Log in</Link>
        </p>
      </div>
    );
  }

  return (
    <dl style={{ display: "grid", gap: "0.75rem" }}>
      <div>
        <dt style={{ color: "var(--muted)" }}>Username</dt>
        <dd>{user.username}</dd>
      </div>
      <div>
        <dt style={{ color: "var(--muted)" }}>Email</dt>
        <dd>{user.email}</dd>
      </div>
      <div>
        <dt style={{ color: "var(--muted)" }}>Member since</dt>
        <dd>{new Date(user.created_at).toLocaleDateString()}</dd>
      </div>
    </dl>
  );
}
