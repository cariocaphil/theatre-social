"use client";

import { useId, useState } from "react";

const STAR_INDEXES = [1, 2, 3, 4, 5];

/**
 * Plain-text star rendering used for read-only display (diary list, e.g.
 * "★★★★½" for 4.5). Kept separate from `StarRatingInput` since read-only
 * contexts don't need any interactivity or a11y affordances beyond text.
 */
export function formatStars(rating: number): string {
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating - fullStars >= 0.5;
  return "★".repeat(fullStars) + (hasHalfStar ? "½" : "");
}

interface StarRatingInputProps {
  value: number | null;
  onChange: (value: number | null) => void;
  disabled?: boolean;
}

/**
 * Interactive 0.5-5 star rating control, half-star increments, clearable.
 *
 * Each star renders two overlaid, transparent `<input type="radio">`
 * elements (left half = X.5, right half = X.0) sharing one `name`, so the
 * browser gives the whole widget native radiogroup semantics (arrow-key
 * navigation, single-selection, screen-reader announcement of each
 * option's `aria-label`) for free, without a UI library. "Clear rating"
 * is a separate real button since no radio option represents "no
 * rating" -- clearing isn't a 11th rating value.
 */
export function StarRatingInput({ value, onChange, disabled = false }: StarRatingInputProps) {
  const name = useId();
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  const displayValue = hoverValue ?? value ?? 0;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
      <div
        role="radiogroup"
        aria-label="Rating"
        style={{ display: "inline-flex" }}
        onMouseLeave={() => setHoverValue(null)}
      >
        {STAR_INDEXES.map((starIndex) => {
          const isFull = displayValue >= starIndex;
          const isHalf = !isFull && displayValue >= starIndex - 0.5;

          return (
            <span
              key={starIndex}
              style={{
                position: "relative",
                display: "inline-block",
                width: "1.6rem",
                height: "1.6rem",
                fontSize: "1.6rem",
                lineHeight: 1,
              }}
            >
              <span aria-hidden style={{ position: "absolute", inset: 0, color: "var(--border)" }}>
                ★
              </span>
              {(isFull || isHalf) && (
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    inset: 0,
                    overflow: "hidden",
                    width: isFull ? "100%" : "50%",
                    color: "#f0a500",
                  }}
                >
                  ★
                </span>
              )}
              <input
                type="radio"
                name={name}
                checked={value === starIndex - 0.5}
                onChange={() => onChange(starIndex - 0.5)}
                onMouseEnter={() => setHoverValue(starIndex - 0.5)}
                onFocus={() => setHoverValue(starIndex - 0.5)}
                disabled={disabled}
                aria-label={`${starIndex - 0.5} stars`}
                style={{
                  position: "absolute",
                  inset: "0 50% 0 0",
                  margin: 0,
                  opacity: 0,
                  cursor: disabled ? "not-allowed" : "pointer",
                }}
              />
              <input
                type="radio"
                name={name}
                checked={value === starIndex}
                onChange={() => onChange(starIndex)}
                onMouseEnter={() => setHoverValue(starIndex)}
                onFocus={() => setHoverValue(starIndex)}
                disabled={disabled}
                aria-label={`${starIndex} star${starIndex === 1 ? "" : "s"}`}
                style={{
                  position: "absolute",
                  inset: "0 0 0 50%",
                  margin: 0,
                  opacity: 0,
                  cursor: disabled ? "not-allowed" : "pointer",
                }}
              />
            </span>
          );
        })}
      </div>
      <button
        type="button"
        onClick={() => onChange(null)}
        disabled={disabled || value === null}
        style={{ fontSize: "0.85rem" }}
      >
        Clear rating
      </button>
      <span aria-live="polite" style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
        {value !== null ? `${value} / 5` : "No rating"}
      </span>
    </div>
  );
}
