"use client";

import { useEffect, useId, useRef, useState, type FormEvent, type MouseEvent } from "react";
import { StarRatingInput } from "@/components/star-rating";
import {
  createDiaryEntry,
  updateDiaryEntry,
  MAX_REVIEW_LENGTH,
  type DiaryEntry,
} from "@/lib/diary";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function todayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

interface LogDialogProps {
  productionId: string;
  productionTitle: string;
  /** Present when editing an existing entry; absent when logging a new one. */
  entry?: DiaryEntry | null;
  onClose: () => void;
  onSaved: (entry: DiaryEntry) => void;
}

type PublicationChoice = "private" | "publish" | "unpublish";

/**
 * Log/review dialog, reused for both creating and editing a `DiaryEntry`
 * (see `entry` prop). Built on the native `<dialog>` element rather than a
 * hand-rolled modal: `showModal()` gives focus trapping, Escape-to-close,
 * and focus restoration on close for free, without a UI library.
 *
 * When review text is non-empty, optional publication controls appear.
 * Attendance is always saved; publication is atomic with create/update via
 * `publish_review` on the diary API.
 */
export function LogDialog({
  productionId,
  productionTitle,
  entry,
  onClose,
  onSaved,
}: LogDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const publicationGroupId = useId();

  const wasPublished = Boolean(entry?.published_at);

  const [watchedAt, setWatchedAt] = useState(entry?.watched_at ?? todayIsoDate());
  const [rating, setRating] = useState<number | null>(entry?.rating ?? null);
  const [review, setReview] = useState(entry?.review ?? "");
  const [publication, setPublication] = useState<PublicationChoice>(
    wasPublished ? "publish" : "private",
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasReviewText = review.trim().length > 0;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (!dialog.open) {
      dialog.showModal();
    }

    dialog.addEventListener("close", onClose);
    return () => dialog.removeEventListener("close", onClose);
  }, [onClose]);

  function handleBackdropClick(event: MouseEvent<HTMLDialogElement>) {
    if (event.target === dialogRef.current) {
      dialogRef.current?.close();
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;

    if (!watchedAt) {
      setError("Please choose the date you attended.");
      return;
    }
    if (watchedAt > todayIsoDate()) {
      setError("The attendance date cannot be in the future.");
      return;
    }

    const trimmedReview = review.trim();
    if (hasReviewText && publication === "publish" && trimmedReview === "") {
      setError("Cannot publish without review text.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    let publishReview: boolean | undefined;
    if (trimmedReview === "") {
      // No review text: never ask to publish; if was published, unpublish.
      publishReview = wasPublished ? false : undefined;
    } else if (publication === "publish") {
      publishReview = true;
    } else if (publication === "unpublish" || (wasPublished && publication === "private")) {
      publishReview = false;
    } else if (!wasPublished && publication === "private") {
      publishReview = false;
    }

    const result = entry
      ? await updateDiaryEntry(PUBLIC_API_URL, entry.id, {
          watched_at: watchedAt,
          rating,
          review: trimmedReview === "" ? null : trimmedReview,
          ...(publishReview !== undefined ? { publish_review: publishReview } : {}),
        })
      : await createDiaryEntry(PUBLIC_API_URL, {
          production_id: productionId,
          watched_at: watchedAt,
          rating,
          review: trimmedReview === "" ? null : trimmedReview,
          publish_review: publication === "publish",
        });

    setIsSubmitting(false);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    onSaved(result.data);
    dialogRef.current?.close();
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onClick={handleBackdropClick}
      style={{
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "1.5rem",
        maxWidth: "28rem",
        width: "90vw",
        color: "var(--foreground)",
        background: "var(--background)",
      }}
    >
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "1rem" }}>
        <h2 id={titleId}>{entry ? "Edit log" : "Log this production"}</h2>
        <p style={{ color: "var(--muted)" }}>{productionTitle}</p>

        <div style={{ display: "grid", gap: "0.25rem" }}>
          <label htmlFor="log-watched-at">Date attended</label>
          <input
            id="log-watched-at"
            type="date"
            value={watchedAt}
            max={todayIsoDate()}
            onChange={(event) => setWatchedAt(event.target.value)}
            disabled={isSubmitting}
            required
          />
        </div>

        <fieldset style={{ border: "none", padding: 0, display: "grid", gap: "0.25rem" }}>
          <legend style={{ padding: 0, marginBottom: "0.25rem" }}>Rating (optional)</legend>
          <StarRatingInput value={rating} onChange={setRating} disabled={isSubmitting} />
        </fieldset>

        <div style={{ display: "grid", gap: "0.25rem" }}>
          <label htmlFor="log-review">Review (optional)</label>
          <textarea
            id="log-review"
            value={review}
            onChange={(event) => {
              const next = event.target.value;
              setReview(next);
              if (next.trim() === "" && !wasPublished) {
                setPublication("private");
              }
            }}
            maxLength={MAX_REVIEW_LENGTH}
            rows={4}
            disabled={isSubmitting}
          />
          <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
            {review.length} / {MAX_REVIEW_LENGTH}
          </span>
        </div>

        {hasReviewText && (
          <fieldset
            style={{ border: "1px solid var(--border)", borderRadius: "6px", padding: "0.75rem" }}
          >
            <legend id={publicationGroupId} style={{ padding: "0 0.25rem" }}>
              Review visibility
            </legend>
            {wasPublished && (
              <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
                This review is currently published.
              </p>
            )}
            <div
              role="radiogroup"
              aria-labelledby={publicationGroupId}
              style={{ display: "grid", gap: "0.5rem" }}
            >
              <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="review-publication"
                  value="private"
                  checked={publication === "private" || publication === "unpublish"}
                  onChange={() => setPublication(wasPublished ? "unpublish" : "private")}
                  disabled={isSubmitting}
                />
                {wasPublished ? "Unpublish review (make private)" : "Keep review private"}
              </label>
              <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="review-publication"
                  value="publish"
                  checked={publication === "publish"}
                  onChange={() => setPublication("publish")}
                  disabled={isSubmitting}
                />
                {wasPublished ? "Keep review published" : "Publish review"}
              </label>
            </div>
          </fieldset>
        )}

        {error && (
          <p role="alert" style={{ color: "var(--error)" }}>
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
          <button type="button" onClick={() => dialogRef.current?.close()} disabled={isSubmitting}>
            Cancel
          </button>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
