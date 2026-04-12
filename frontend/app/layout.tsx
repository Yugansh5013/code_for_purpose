import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "OmniData — AI Data Intelligence",
  description: "Enterprise analytics terminal powered by multi-source AI"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
