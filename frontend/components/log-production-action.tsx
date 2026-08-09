"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { LogDialog } from "@/components/log-dialog";
import type { DiaryEntry } from "@/lib/diary";

interface LogProductionActionProps {
  productionId: string;
  productionTitle: string;
}

/**
 * Primary "Log this production" action on the production detail page.
 * Reuses the existing `useAuth` session state rather than tracking its own
 * authentication status, and follows the same unauthenticated-prompt
 * pattern as `AccountSummary` (a message plus a link to `/login`) instead
 * of inventing a second auth UX.
 */
export function LogProductionAction({ productionId, productionTitle }: LogProductionActionProps) {
  const { status } = useAuth();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [lastSaved, setLastSaved] = useState<DiaryEntry | null>(null);

  if (status === "loading") {
    return null;
  }

  if (status !== "authenticated") {
    return (
      <p>
        <Link href="/login">Log in</Link> to log this production.
      </p>
    );
  }

  return (
    <div>
      <button type="button" onClick={() => setIsDialogOpen(true)}>
        Log this production
      </button>

      {lastSaved && (
        <p role="status" style={{ color: "var(--success)", marginTop: "0.5rem" }}>
          Logged for {lastSaved.watched_at}. <Link href="/diary">View your diary</Link>
        </p>
      )}

      {isDialogOpen && (
        <LogDialog
          productionId={productionId}
          productionTitle={productionTitle}
          onClose={() => setIsDialogOpen(false)}
          onSaved={(entry) => {
            setLastSaved(entry);
            setIsDialogOpen(false);
          }}
        />
      )}
    </div>
  );
}
