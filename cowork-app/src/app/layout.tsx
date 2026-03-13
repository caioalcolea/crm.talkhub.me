import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sala Cowork — TalkHub",
  description: "Virtual coworking space",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" style={{ height: "100%" }}>
      <body style={{ margin: 0, padding: 0, overflow: "hidden", width: "100%", height: "100%" }}>
        {children}
      </body>
    </html>
  );
}
