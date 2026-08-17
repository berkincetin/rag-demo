import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Şirket Bilgi Asistanı",
  description:
    "Altı şirket belgesi üzerinde atıflı soru-cevap yapan RAG agent arayüzü.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body className="antialiased">{children}</body>
    </html>
  );
}
