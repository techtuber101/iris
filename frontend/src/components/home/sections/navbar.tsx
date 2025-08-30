"use client";

import { Icons } from "@/components/home/icons";
import { NavMenu } from "@/components/home/nav-menu";
import { ThemeToggle } from "@/components/home/theme-toggle";
import { siteConfig } from "@/lib/home";
import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";
import { AnimatePresence, motion, useScroll } from "motion/react";
import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { useAuth } from "@/components/AuthProvider";

const INITIAL_WIDTH = "70rem";
const MAX_WIDTH = "800px";

const overlayVariants = { hidden: { opacity: 0 }, visible: { opacity: 1 }, exit: { opacity: 0 } };
const drawerVariants = {
  hidden: { opacity: 0, y: 100 },
  visible: { opacity: 1, y: 0, rotate: 0, transition: { type: "spring", damping: 15, stiffness: 200, staggerChildren: 0.03 } },
  exit: { opacity: 0, y: 100, transition: { duration: 0.1 } },
};
const drawerMenuContainerVariants = { hidden: { opacity: 0 }, visible: { opacity: 1 } };
const drawerMenuVariants = { hidden: { opacity: 0 }, visible: { opacity: 1 } };

export function Navbar() {
  const { scrollY } = useScroll();
  const [hasScrolled, setHasScrolled] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("hero");
  const { theme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const { user } = useAuth();

  useEffect(() => setMounted(true), []);

  // Highlight current section
  useEffect(() => {
    const handleScroll = () => {
      const sections = siteConfig.nav.links.map((item) => item.href.substring(1));
      for (const section of sections) {
        const el = document.getElementById(section);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        if (rect.top <= 150 && rect.bottom >= 150) {
          setActiveSection(section);
          break;
        }
      }
    };
    window.addEventListener("scroll", handleScroll);
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Toggle glass on scroll
  useEffect(() => {
    const unsub = scrollY.on("change", (latest) => setHasScrolled(latest > 10));
    return unsub;
  }, [scrollY]);

  const toggleDrawer = () => setIsDrawerOpen((p) => !p);
  const handleOverlayClick = () => setIsDrawerOpen(false);

  const logoSrc = "/iris-logo.png";

  return (
    <header
      className={cn(
        // CENTERED, FLOATING “PILL” CONTAINER
        "fixed top-4 left-1/2 -translate-x-1/2 z-50 transition-all duration-300"
      )}
      // ensure the centered container doesn't get clipped on tiny screens
      style={{ width: "min(100vw - 1rem, 80rem)" }}
    >
      {/* Animate the container width as you scroll (keeps it centered) */}
      <motion.div
        className="mx-auto"
        initial={{ width: INITIAL_WIDTH }}
        animate={{ width: hasScrolled ? MAX_WIDTH : INITIAL_WIDTH }}
        transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <div
          className={cn(
            // The pill itself
            "rounded-full transition-all duration-300",
            hasScrolled
              // scrolled: glassy pill
              ? "border border-border bg-background/70 backdrop-blur-md shadow-lg px-2"
              // top: totally transparent — no bg, no border, no blur, no shadow
              : "border-transparent bg-transparent backdrop-blur-0 shadow-none px-7"
          )}
        >
          <div className="flex h-[56px] items-center justify-between px-4 md:px-6">
            {/* Left: Logo */}
            <Link href="/" className="flex items-center gap-3">
              <Image src={logoSrc} alt="Iris Logo" width={140} height={22} priority />
            </Link>

            {/* Center: Menu */}
            <NavMenu />

            {/* Right: Actions */}
            <div className="flex flex-row items-center gap-1 md:gap-3 shrink-0">
              <div className="hidden md:flex items-center space-x-3">
                {user ? (
                  <Link
                    className="bg-secondary h-8 flex items-center justify-center text-sm font-normal tracking-wide rounded-full text-primary-foreground dark:text-secondary-foreground w-fit px-4 shadow-[inset_0_1px_2px_rgba(255,255,255,0.25),0_3px_3px_-1.5px_rgba(16,24,40,0.06),0_1px_1px_rgba(16,24,40,0.08)] border border-white/[0.12]"
                    href="/dashboard"
                  >
                    Dashboard
                  </Link>
                ) : (
                  <Link
                    className="bg-secondary h-8 flex items-center justify-center text-sm font-normal tracking-wide rounded-full text-primary-foreground dark:text-secondary-foreground w-fit px-4 shadow-[inset_0_1px_2px_rgba(255,255,255,0.25),0_3px_3px_-1.5px_rgba(16,24,40,0.06),0_1px_1px_rgba(16,24,40,0.08)] border border-white/[0.12]"
                    href="/auth"
                  >
                    Get Started
                  </Link>
                )}
              </div>
              <ThemeToggle />
              <button
                className="md:hidden border border-border size-8 rounded-md cursor-pointer flex items-center justify-center"
                onClick={toggleDrawer}
              >
                {isDrawerOpen ? <X className="size-5" /> : <Menu className="size-5" />}
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {isDrawerOpen && (
          <>
            <motion.div
              className="fixed inset-0 bg-black/50 backdrop-blur-sm"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={overlayVariants}
              transition={{ duration: 0.2 }}
              onClick={handleOverlayClick}
            />
            <motion.div
              className="fixed inset-x-0 w-[95%] mx-auto bottom-3 bg-background border border-border p-4 rounded-xl shadow-lg"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={drawerVariants}
            >
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <Link href="/" className="flex items-center gap-3">
                    <Image src={logoSrc} alt="Iris Logo" width={120} height={22} priority />
                    <span className="font-medium text-primary text-sm">Iris</span>
                  </Link>
                  <button onClick={toggleDrawer} className="border border-border rounded-md p-1 cursor-pointer">
                    <X className="size-5" />
                  </button>
                </div>

                <motion.ul className="flex flex-col text-sm mb-4 border border-border rounded-md" variants={drawerMenuContainerVariants}>
                  <AnimatePresence>
                    {siteConfig.nav.links.map((item) => (
                      <motion.li key={item.id} className="p-2.5 border-b border-border last:border-b-0" variants={drawerMenuVariants}>
                        <a
                          href={item.href}
                          onClick={(e) => {
                            e.preventDefault();
                            const el = document.getElementById(item.href.substring(1));
                            el?.scrollIntoView({ behavior: "smooth" });
                            setIsDrawerOpen(false);
                          }}
                          className={cn(
                            "underline-offset-4 hover:text-primary/80 transition-colors",
                            activeSection === item.href.substring(1) ? "text-primary font-medium" : "text-primary/60"
                          )}
                        >
                          {item.name}
                        </a>
                      </motion.li>
                    ))}
                  </AnimatePresence>
                </motion.ul>

                <div className="flex flex-col gap-2">
                  {user ? (
                    <Link
  href="/dashboard"
  className={cn(
    "relative inline-flex items-center px-4 py-2 rounded-xl text-sm font-medium transition-all",
    // glassy base
    "bg-gradient-to-r from-blue-500/70 via-indigo-500/60 to-purple-500/70",
    "backdrop-blur-md border border-white/10",
    // text + subtle glow
    "text-white shadow-[0_0_12px_rgba(99,102,241,0.6)]",
    // hover effect = stronger glow + lift
    "hover:shadow-[0_0_20px_rgba(99,102,241,0.9)] hover:scale-[1.03]",
    // active = slight press
    "active:scale-[0.97]"
  )}
>
  Dashboard
</Link>

                  ) : (
                    <Link
                      href="/auth"
                      className="bg-secondary h-8 flex items-center justify-center text-sm font-normal tracking-wide rounded-full text-primary-foreground dark:text-secondary-foreground w-full px-4 shadow-[inset_0_1px_2px_rgba(255,255,255,0.25),0_3px_3px_-1.5px_rgba(16,24,40,0.06),0_1px_1px_rgba(16,24,40,0.08)] border border-white/[0.12] hover:bg-secondary/80 transition-all ease-out active:scale-95"
                    >
                      Get Started
                    </Link>
                  )}
                  <div className="flex justify-between">
                    <ThemeToggle />
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </header>
  );
}
