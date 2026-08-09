"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useAuth } from "@/components/auth-provider";

const MIN_PASSWORD_LENGTH = 8;

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!username.trim() || !email.trim() || !password) {
      setError("Username, email, and password are all required.");
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }

    setError(null);
    setIsSubmitting(true);
    const result = await register(username, email, password);
    setIsSubmitting(false);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    router.push("/");
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Sign up" style={{ display: "grid", gap: "1rem" }}>
      <div style={{ display: "grid", gap: "0.25rem" }}>
        <label htmlFor="register-username">Username</label>
        <input
          id="register-username"
          name="username"
          type="text"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
      </div>

      <div style={{ display: "grid", gap: "0.25rem" }}>
        <label htmlFor="register-email">Email</label>
        <input
          id="register-email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>

      <div style={{ display: "grid", gap: "0.25rem" }}>
        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          name="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </div>

      {error && (
        <p role="alert" style={{ color: "var(--error)" }}>
          {error}
        </p>
      )}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Signing up…" : "Sign up"}
      </button>
    </form>
  );
}
