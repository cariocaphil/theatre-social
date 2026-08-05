import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Theatre Social",
  description: "Theatre Social - foundation MVP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
