"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { LogDialog } from "@/components/log-dialog";
import { formatStars } from "@/components/star-rating";
import { deleteDiaryEntry, fetchDiaryEntries, type DiaryEntry } from "@/lib/diary";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatWatchedAt(isoDate: string): string {
  // Parsed as UTC-midnight, consistent with a plain calendar date (no
  // time-of-day, no timezone) rather than letting the browser's local
  // timezone shift it to the previous day.
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

function DiaryEntryRow({
  entry,
  onEdit,
  onDelete,
}: {
  entry: DiaryEntry;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    await onDelete();
    setIsDeleting(false);
    setConfirmingDelete(false);
  }

  return (
    <li style={{ borderBottom: "1px solid var(--border)", padding: "1.25rem 0" }}>
      <p style={{ color: "var(--muted)" }}>{formatWatchedAt(entry.watched_at)}</p>
      <Link href={`/productions/${entry.production.slug}`}>
        <h2 style={{ fontSize: "1.15rem" }}>{entry.production.title}</h2>
      </Link>
      {entry.production.venue_name && (
        <p style={{ color: "var(--muted)" }}>{entry.production.venue_name}</p>
      )}
      {entry.rating !== null && (
        <p aria-label={`Rating: ${entry.rating} out of 5 stars`}>{formatStars(entry.rating)}</p>
      )}
      {entry.review && <p style={{ marginTop: "0.25rem" }}>{entry.review}</p>}

      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.5rem" }}>
        <button type="button" onClick={onEdit}>
          Edit
        </button>
        {confirmingDelete ? (
          <>
            <span>Delete this entry?</span>
            <button type="button" onClick={handleConfirmDelete} disabled={isDeleting}>
              {isDeleting ? "Deleting…" : "Confirm delete"}
            </button>
            <button type="button" onClick={() => setConfirmingDelete(false)} disabled={isDeleting}>
              Cancel
            </button>
          </>
        ) : (
          <button type="button" onClick={() => setConfirmingDelete(true)}>
            Delete
          </button>
        )}
      </div>
    </li>
  );
}

/**
 * Authenticated `/diary` content. A Client Component (not the page itself)
 * because it depends on `useAuth` and needs to fetch with the browser's
 * session cookie -- the same pattern already used by `AccountSummary` for
 * `/me`, rather than inventing server-side cookie forwarding.
 */
export function DiaryList() {
  const { status } = useAuth();
  const [entries, setEntries] = useState<DiaryEntry[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editingEntry, setEditingEntry] = useState<DiaryEntry | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadEntries = useCallback(async () => {
    const result = await fetchDiaryEntries(PUBLIC_API_URL);
    if (!result.ok) {
      setLoadError(result.error);
      return;
    }
    setLoadError(null);
    setEntries(result.data.items);
  }, []);

  useEffect(() => {
    if (status === "authenticated") {
      loadEntries();
    }
  }, [status, loadEntries]);

  async function handleDelete(entryId: string) {
    setActionError(null);
    const result = await deleteDiaryEntry(PUBLIC_API_URL, entryId);
    if (!result.ok) {
      setActionError(result.error);
      return;
    }
    setEntries((current) => current?.filter((entry) => entry.id !== entryId) ?? current);
  }

  if (status === "loading" || (status === "authenticated" && entries === null && !loadError)) {
    return <p role="status">Loading diary…</p>;
  }

  if (status !== "authenticated") {
    return (
      <div role="alert">
        <p>You need to be logged in to view your diary.</p>
        <p>
          <Link href="/login">Log in</Link>
        </p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div role="alert" style={{ color: "var(--error)" }}>
        <p>Could not load your diary.</p>
        <p>{loadError}</p>
      </div>
    );
  }

  return (
    <div>
      {actionError && (
        <p role="alert" style={{ color: "var(--error)" }}>
          {actionError}
        </p>
      )}

      {entries && entries.length === 0 ? (
        <div style={{ marginTop: "1.5rem" }}>
          <p style={{ color: "var(--muted)" }}>You haven&apos;t logged any productions yet.</p>
          <p style={{ marginTop: "0.5rem" }}>
            <Link href="/productions">Browse the production catalogue</Link>
          </p>
        </div>
      ) : (
        <ul style={{ listStyle: "none", marginTop: "1.5rem" }}>
          {entries?.map((entry) => (
            <DiaryEntryRow
              key={entry.id}
              entry={entry}
              onEdit={() => setEditingEntry(entry)}
              onDelete={() => handleDelete(entry.id)}
            />
          ))}
        </ul>
      )}

      {editingEntry && (
        <LogDialog
          productionId={editingEntry.production_id}
          productionTitle={editingEntry.production.title}
          entry={editingEntry}
          onClose={() => setEditingEntry(null)}
          onSaved={(updated) => {
            setEntries(
              (current) =>
                current?.map((existing) => (existing.id === updated.id ? updated : existing)) ??
                current,
            );
            setEditingEntry(null);
          }}
        />
      )}
    </div>
  );
}
