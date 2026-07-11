import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Evidra",
  description: "Evidra",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt">
      <body>{children}</body>
    </html>
  );
}

