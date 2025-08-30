"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export type ChatMessage = { id: string; role: "user" | "assistant"; content: string };

// -----------------------------
// Local storage for tiny chat
// -----------------------------
function useLocalMessages(storageKey: string, initial: ChatMessage[]) {
  const [messages, setMessages] = useState<ChatMessage[]>(initial);

  useEffect(() => {
    try {
      const raw = typeof window !== "undefined" && window.localStorage.getItem(storageKey);
      if (raw) setMessages(JSON.parse(raw));
    } catch {}
  }, [storageKey]);

  useEffect(() => {
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(storageKey, JSON.stringify(messages));
      }
    } catch {}
  }, [messages, storageKey]);

  return { messages, setMessages } as const;
}

// -----------------------------
// Glass primitives (match site)
// -----------------------------
const baseGlass =
  "relative rounded-3xl border border-white/10 bg-[rgba(10,14,22,0.55)] backdrop-blur-2xl shadow-[0_20px_60px_-10px_rgba(0,0,0,0.8),inset_0_1px_0_0_rgba(255,255,255,0.06)] overflow-hidden";

function GlassCard({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={`${baseGlass} ${className}`}>
      {/* Gradient rim (subtle) */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-3xl"
        style={{
          background:
            "linear-gradient(180deg, rgba(173,216,255,0.18), rgba(255,255,255,0.04) 30%, rgba(150,160,255,0.14) 85%, rgba(255,255,255,0.06))",
          WebkitMask: "linear-gradient(#000,#000) content-box, linear-gradient(#000,#000)",
          WebkitMaskComposite: "xor" as any,
          maskComposite: "exclude",
          padding: 1,
          borderRadius: 24,
        }}
      />
      {/* Specular streak */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-24"
        style={{
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0.06) 45%, rgba(255,255,255,0) 100%)",
          filter: "blur(6px)",
          mixBlendMode: "screen",
        }}
      />
      {/* Fine noise */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            "url('data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'60\' height=\'60\'><filter id=\'n\'><feTurbulence type=\'fractalNoise\' baseFrequency=\'0.8\' numOctaves=\'4\'/><feColorMatrix type=\'saturate\' values=\'0\'/><feComponentTransfer><feFuncA type=\'table\' tableValues=\'0 0.03\'/></feComponentTransfer></filter><rect width=\'100%\' height=\'100%\' filter=\'url(%23n)\' /></svg>')",
          backgroundSize: "100px 100px",
          mixBlendMode: "overlay",
        }}
      />
      {/* Corner screws */}
      <div className="pointer-events-none" aria-hidden>
        <div className="absolute left-3 top-3 h-1.5 w-1.5 rounded-full bg-white/30" />
        <div className="absolute right-3 top-3 h-1.5 w-1.5 rounded-full bg-white/30" />
        <div className="absolute left-3 bottom-3 h-1.5 w-1.5 rounded-full bg-white/30" />
        <div className="absolute right-3 bottom-3 h-1.5 w-1.5 rounded-full bg-white/30" />
      </div>
      {children}
    </div>
  );
}

function ChatBubble({ messages, onSend }: { messages: ChatMessage[]; onSend: (text: string) => void }) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setText("");
    onSend(t);
  };

  return (
    <div className="flex flex-col gap-3">
      <div
        ref={listRef}
        className="max-h-[38vh] min-h-[22vh] overflow-y-auto rounded-2xl border border-white/10 bg-[rgba(7,10,17,0.6)] p-3 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04)]"
      >
        {messages.map((m) => (
          <div key={m.id} className="mb-2 flex">
            <div
              className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed ring-1 shadow-[0_10px_20px_-10px_rgba(0,0,0,0.6)] ${
                m.role === "user" ? "ml-auto bg-white/10 ring-white/15" : "bg-white/5 ring-white/10"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={submit} className="flex items-center gap-2">
        <input
          type="text"
          aria-label="Ask Iris"
          placeholder="Ask Iris anything…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="h-11 flex-1 rounded-2xl border border-white/15 bg-white/5 px-4 text-sm placeholder:text-white/40 outline-none ring-0 backdrop-blur-sm focus:border-white/25"
        />
        <button
          type="submit"
          className="h-11 rounded-2xl border border-white/20 bg-white/10 px-4 text-sm text-white/90 transition hover:border-white/30 hover:bg-white/15 active:translate-y-[1px]"
        >
          Send
        </button>
      </form>
    </div>
  );
}

// -----------------------------
// Main component
// -----------------------------
type HeroProps = {
  title?: string;
  product?: string;
  subhead?: string;
  irisTitle?: string;
  storageKey?: string;
  /** Optional: override the destination after capturing pending prompt */
  returnUrl?: string; // default "/dashboard"
};

const PENDING_PROMPT_KEY = "pendingAgentPrompt";

const HeroSection: React.FC<HeroProps> = ({
  title = "Iris",
  product = "Introducing",
  subhead = "The world's best agentic AI",
  irisTitle = "Iris",
  storageKey = "iris.chat",
  returnUrl = "/dashboard",
}) => {
  const seed: ChatMessage[] = useMemo(
    () => [{ id: "seed-assistant", role: "assistant", content: "Hey, I’m Iris — ask me anything." }],
    []
  );

  const { messages, setMessages } = useLocalMessages(storageKey, seed);
  const router = useRouter();
  const { user } = useAuth();

  const handleSend = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(PENDING_PROMPT_KEY, trimmed);
      }
      const to = user ? returnUrl : `/auth?mode=signin&returnUrl=${encodeURIComponent(returnUrl)}`;
      router.push(to);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <section className="relative min-h-[92vh] w-full overflow-hidden pt-[120px] text-white">
      {/* very soft local halo to keep hero focus without duplicating the global spotlight */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-10 h-72 blur-3xl opacity-40"
        style={{
          background:
            "radial-gradient(60% 60% at 50% 0%, rgba(120,160,255,0.18), rgba(120,160,255,0.06) 55%, transparent 85%)",
          mixBlendMode: "screen",
        }}
      />

      {/* Content container */}
      <div className="relative mx-auto flex h-full max-w-6xl flex-col items-center justify-center px-6 py-24">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-2 text-sm/6 text-white/70"
        >
          {product}
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="bg-gradient-to-b from-white to-white/70 bg-clip-text text-center text-7xl font-semibold tracking-tight text-transparent md:text-8xl"
        >
          {title}
        </motion.h1>

        {/* Subhead */}
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-4 max-w-2xl text-balance text-center text-lg text-white/70"
        >
          {subhead}
        </motion.p>

        {/* Card stack */}
        <div className="relative mt-12 w-full max-w-6xl">
          {/* Left placeholder card */}
          <motion.div
            initial={{ opacity: 0, x: -40, rotate: -6 }}
            animate={{ opacity: 1, x: 0, rotate: -6 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="absolute left-[-4%] top-8 hidden w-[42%] -rotate-6 p-6 md:block pointer-events-none"
          >
            <GlassCard>
              <div className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <div className="h-6 w-6 rounded-full bg-white/10 ring-1 ring-white/15" />
                  <div className="h-3 w-28 rounded bg-white/10" />
                </div>
                <PlaceholderCard direction="left" />
              </div>
            </GlassCard>
          </motion.div>

          {/* Right placeholder card */}
          <motion.div
            initial={{ opacity: 0, x: 40, rotate: 6 }}
            animate={{ opacity: 1, x: 0, rotate: 6 }}
            transition={{ duration: 0.6, delay: 0.38 }}
            className="absolute right-[-4%] top-8 hidden w-[42%] rotate-6 p-6 md:block pointer-events-none"
          >
            <GlassCard>
              <div className="p-6">
                <div className="mb-4 flex items-center gap-2">
                  <div className="h-6 w-6 rounded-full bg-white/10 ring-1 ring-white/15" />
                  <div className="h-3 w-28 rounded bg-white/10" />
                </div>
                <PlaceholderCard direction="right" />
              </div>
            </GlassCard>
          </motion.div>

          {/* Center interactive chat card */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.45 }}
            className="relative z-10 mx-auto w-[92%] p-0 md:w-[58%]"
          >
            <GlassCard>
              <div className="p-6 md:p-7">
                <header className="mb-4 flex items-center gap-2">
                  <div className="h-6 w-6 rounded-full bg-white/10 ring-1 ring-white/20" />
                  <h3 className="text-sm font-medium text-white/80">Sign in to {irisTitle}</h3>
                </header>
                <ChatBubble messages={messages} onSend={handleSend} />
              </div>
            </GlassCard>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

function PlaceholderCard({ direction }: { direction: "left" | "right" }) {
  return (
    <div className="pointer-events-none select-none opacity-80">
      <div className="mb-4 flex items-center gap-2">
        <div className="h-6 w-6 rounded-full bg-white/10 ring-1 ring-white/15" />
        <div className="h-3 w-28 rounded bg-white/10" />
      </div>
      <div className="space-y-2">
        <div className="h-9 w-full rounded-xl bg-white/5 ring-1 ring-white/10" />
        <div className="h-9 w-full rounded-xl bg-white/5 ring-1 ring-white/10" />
        <div className="h-9 w-2/3 rounded-xl bg-white/5 ring-1 ring-white/10" />
      </div>
      <div
        className={`mt-5 h-9 ${direction === "left" ? "w-1/2" : "w-2/3"} rounded-xl bg-white/10 ring-1 ring-white/15`}
      />
    </div>
  );
}

export default HeroSection;
export { HeroSection };
