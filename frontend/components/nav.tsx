"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";

export function Nav() {
  const { status, user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
  }

  return (
    <nav
      aria-label="Account"
      style={{
        display: "flex",
        justifyContent: "flex-end",
        alignItems: "center",
        gap: "1rem",
        padding: "1rem 1.5rem",
        borderBottom: "1px solid var(--border)",
      }}
    >
      {status === "loading" ? null : status === "authenticated" && user ? (
        <div style={{ position: "relative" }}>
          <button type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen}>
            {user.username.toUpperCase()} &#9662;
          </button>
          {menuOpen && (
            <div
              role="menu"
              style={{
                position: "absolute",
                right: 0,
                top: "100%",
                marginTop: "0.25rem",
                background: "var(--background)",
                border: "1px solid var(--border)",
                borderRadius: "4px",
                padding: "0.5rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
                minWidth: "8rem",
                zIndex: 10,
              }}
            >
              <Link href="/me" role="menuitem" onClick={() => setMenuOpen(false)}>
                Account
              </Link>
              <button type="button" role="menuitem" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          <Link href="/login">Log in</Link>
          <Link href="/register">Sign up</Link>
        </>
      )}
    </nav>
  );
}
