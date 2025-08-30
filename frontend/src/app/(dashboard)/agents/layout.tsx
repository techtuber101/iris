import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Conversation | Iris",
  description: "Interactive agent conversation powered by Iris",
  openGraph: {
    title: "Agent Conversation | Iris",
    description: "Interactive agent conversation powered by Iris",
    type: "website",
  },
};

export default function AgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
} 