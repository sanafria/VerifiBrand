import type { Metadata } from 'next';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { DemoToolbar } from '@/components/layout/DemoToolbar';
import './globals.css';

export const metadata: Metadata = {
  title: 'VerifiBrand — Pre-Publication Brand Review Workspace',
  description: 'VerifiBrand checks the content. Your people make the decision. Verify drafts against approved brand guidelines, facts, terminology, and assets before publication.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main>{children}</main>
        <DemoToolbar />
        <Footer />
      </body>
    </html>
  );
}
