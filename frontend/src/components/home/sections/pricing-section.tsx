"use client";

import React from "react";
import { SectionHeader } from "@/components/home/section-header";
import { siteConfig } from "@/lib/home";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";
import Link from "next/link";

// ==============================
// Glass primitives (match Hero)
// ==============================
const baseGlass =
  "relative rounded-3xl border border-white/10 bg-[rgba(10,14,22,0.55)] backdrop-blur-2xl shadow-[0_20px_60px_-10px_rgba(0,0,0,0.8),inset_0_1px_0_0_rgba(255,255,255,0.06)] overflow-hidden";

function GlassCard({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn(baseGlass, className)}>
      {/* Gradient rim */}
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
            "url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2260%22 height=%2260%22><filter id=%22n%22><feTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%224%22/><feColorMatrix type=%22saturate%22 values=%220%22/><feComponentTransfer><feFuncA type=%22table%22 tableValues=%220 0.03%22/></feComponentTransfer></filter><rect width=%22100%%22 height=%22100%%22 filter=%22url(%23n)%22 /></svg>')",
          backgroundSize: "100px 100px",
          mixBlendMode: "overlay",
        }}
      />
      {children}
    </div>
  );
}

// ==============================
// Helpers
// ==============================
function getTierMeta(tierName: string) {
  const name = tierName.toLowerCase();
  if (name.includes("free")) {
    return { showCoins: false, coins: "", isEnterprise: false };
  }
  if (name.includes("air")) {
    return { showCoins: true, coins: "10,000 coins", isEnterprise: false };
  }
  if (name.includes("pro")) {
    return { showCoins: true, coins: "Unlimited coins", isEnterprise: false };
  }
  if (name.includes("enterprise")) {
    return { showCoins: false, coins: "", isEnterprise: true };
  }
  return { showCoins: true, coins: "Unlimited coins", isEnterprise: false };
}

const PriceDisplay = ({ price }: { price: string }) => (
  <motion.span
    key={price}
    className="text-4xl font-semibold bg-gradient-to-b from-white to-white/70 bg-clip-text text-transparent"
    initial={{ opacity: 0, x: 10, filter: "blur(5px)" }}
    animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
    transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
  >
    {price}
  </motion.span>
);

// ==============================
// Component
// ==============================
export function PricingSection() {
  return (
    <section
      id="pricing"
      className="relative w-full flex flex-col items-center justify-center gap-10 pb-20"
    >
      <SectionHeader>
        <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-center bg-gradient-to-b from-white to-white/70 bg-clip-text text-transparent">
          General Intelligence available today
        </h2>
        <p className="text-center text-white/70 font-medium text-balance">
          Choose a plan that fits. Iris runs fully managed.
        </p>
      </SectionHeader>

      {/* Pricing grid (cloud only) */}
      <div className="grid min-[650px]:grid-cols-2 min-[1000px]:grid-cols-3 gap-5 w-full max-w-6xl mx-auto px-6">
        {siteConfig.cloudPricingItems.map((tier) => {
          const meta = getTierMeta(tier.name);
          const isEnterprise = meta.isEnterprise;

          // Normalize button text: "Hire Iris" -> "Get Now"
          const rawBtn = tier.buttonText || "";
          const buttonText = rawBtn.toLowerCase() === "hire iris" ? "Get Now" : rawBtn || "Get Now";

          // Build CTA link: prefer Stripe priceId if you route through /checkout, else default to /auth
          const ctaHref = tier.stripePriceId
            ? `/checkout?priceId=${encodeURIComponent(tier.stripePriceId)}`
            : "/auth";

          return (
            <GlassCard
              key={tier.name}
              className={cn(
                "grid grid-rows-[auto_auto_auto] relative h-fit min-[650px]:h-full transition-transform hover:-translate-y-0.5"
              )}
            >
              {/* Header / Price */}
              <div className="p-5 flex flex-col gap-3">
                <p className="text-sm flex items-center">
                  <span className="bg-clip-text text-transparent bg-gradient-to-b from-white to-white/70">
                    {tier.name}
                  </span>
                  {tier.isPopular && (
                    <span className="ml-2 inline-flex items-center h-6 px-2 rounded-full text-xs font-medium text-white bg-white/10 ring-1 ring-white/20">
                      Popular
                    </span>
                  )}
                </p>

                <div className="flex items-baseline mt-1">
                  <PriceDisplay price={tier.price} />
                  <span className="ml-2 text-white/70">{tier.price !== "$0" ? "/month" : ""}</span>
                </div>

                <p className="text-sm text-white/70">{tier.description}</p>

                {/* Coins / Enterprise badge */}
                {meta.showCoins && (
                  <div className="inline-flex items-center rounded-full border border-white/20 bg-white/10 px-2.5 py-0.5 text-xs font-semibold text-white w-fit">
                    {meta.coins}
                  </div>
                )}
                {isEnterprise && (
                  <div className="inline-flex items-center rounded-full border border-white/20 bg-white/10 px-2.5 py-0.5 text-xs font-semibold text-white/80 w-fit">
                    Contact sales
                  </div>
                )}
              </div>

              {/* CTA */}
              <div className="px-5 pb-5">
                {isEnterprise ? (
                  <Link
                    href="/contact"
                    className={cn(
                      "h-10 w-full flex items-center justify-center text-sm tracking-wide rounded-full px-4 transition-all active:scale-[0.99]",
                      "bg-white text-black shadow-[0_10px_20px_-12px_rgba(255,255,255,0.6)] hover:bg-white/90"
                    )}
                  >
                    Contact sales
                  </Link>
                ) : (
                  <Link
                    href={ctaHref}
                    className={cn(
                      "h-10 w-full flex items-center justify-center text-sm tracking-wide rounded-full px-4 transition-all active:scale-[0.99]",
                      "bg-white text-black shadow-[0_10px_20px_-12px_rgba(255,255,255,0.6)] hover:bg-white/90"
                    )}
                  >
                    {buttonText || "Get Now"}
                  </Link>
                )}
              </div>

              {/* Optional features area */}
              <div className="px-5 pb-5">{/* Add tier.features here if desired */}</div>
            </GlassCard>
          );
        })}
      </div>
    </section>
  );
}
