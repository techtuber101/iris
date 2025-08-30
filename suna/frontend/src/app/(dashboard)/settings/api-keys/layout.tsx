import { Metadata } from 'next';

export const metadata: Metadata = {
  // Rebranded metadata for Iris
  title: 'API Keys | Iris',
  description: 'Manage your API keys for programmatic access to Iris',
  openGraph: {
    // Open graph metadata updated for Iris
    title: 'API Keys | Iris',
    description: 'Manage your API keys for programmatic access to Iris',
    type: 'website',
  },
};

export default async function APIKeysLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
