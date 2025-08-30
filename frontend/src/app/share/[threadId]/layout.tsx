import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Shared Conversation',
  description: 'View a shared AI conversation',
  openGraph: {
    title: 'Shared AI Conversation',
    description: 'View a shared AI conversation from Iris',
    // Use the Iris logo for shared conversations.
    images: ['/iris-logo.png'],
  },
};

export default function ThreadLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
} 