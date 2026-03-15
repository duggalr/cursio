"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { Youtube, Twitter } from "lucide-react";
import type { User } from "@supabase/supabase-js";
import type { SupabaseClient } from "@supabase/supabase-js";
import AuthModal from "./AuthModal";

export default function Navbar() {
  const [user, setUser] = useState<User | null>(null);
  const [authModal, setAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const supabaseRef = useRef<SupabaseClient | null>(null);

  useEffect(() => {
    let subscription: { unsubscribe: () => void } | null = null;

    async function init() {
      try {
        const { createClient } = await import("@/lib/supabase");
        const supabase = createClient();
        supabaseRef.current = supabase;

        const { data: { user } } = await supabase.auth.getUser();
        setUser(user);

        const { data: { subscription: sub } } = supabase.auth.onAuthStateChange(
          (_event: string, session: { user: User | null } | null) => {
            setUser(session?.user ?? null);
          }
        );
        subscription = sub;
      } catch {
        // Supabase not configured yet
      }
    }

    init();
    return () => {
      subscription?.unsubscribe();
    };
  }, []);

  const handleSignOut = async () => {
    if (supabaseRef.current) {
      await supabaseRef.current.auth.signOut();
      setUser(null);
    }
  };

  return (
    <>
      <nav className="py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6">
          <Link
            href="/"
            className="text-lg text-[var(--color-foreground)]"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            Lumira
          </Link>

          <div className="flex items-center gap-4">
            <a
              href="https://youtube.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
            >
              <Youtube size={18} />
            </a>
            <a
              href="https://x.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
            >
              <Twitter size={16} />
            </a>

            <div className="mx-1 h-4 w-px bg-[var(--color-border)]" />

            {user ? (
              <>
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-surface-hover)] text-xs font-medium text-[var(--color-muted)]">
                  {user.email?.[0]?.toUpperCase() || "U"}
                </div>
                <button
                  onClick={handleSignOut}
                  className="text-sm text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => { setAuthMode("signin"); setAuthModal(true); }}
                  className="text-sm text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
                >
                  Sign in
                </button>
                <button
                  onClick={() => { setAuthMode("signup"); setAuthModal(true); }}
                  className="rounded-lg bg-[var(--color-foreground)] px-3.5 py-1.5 text-sm font-medium text-[var(--color-background)] transition-opacity hover:opacity-80"
                >
                  Sign up
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      <AuthModal isOpen={authModal} onClose={() => setAuthModal(false)} initialMode={authMode} />
    </>
  );
}
