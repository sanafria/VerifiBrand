import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "./context/AppContext";
import ClientLayout from "./components/ClientLayout";

export const metadata: Metadata = {
  title: "VerifiBrand — Content Governance Platform",
  description: "The evidence-backed gate for everything your brand publishes. Verify content against versioned brand rules, approved facts, and trusted assets before publication.",
  keywords: "brand governance, content compliance, policy cards, content passport, brand management",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <ClientLayout>{children}</ClientLayout>
        </AppProvider>
      </body>
    </html>
  );
}
