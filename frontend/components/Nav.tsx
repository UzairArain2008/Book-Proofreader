"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/books", label: "Books" },
  { href: "/upload", label: "Upload" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-ink/10 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-display text-xl font-semibold tracking-tight text-ink">
            Proofreader
          </span>
          <span className="font-mono-data text-[11px] uppercase tracking-[0.18em] text-accent">
            for publishers
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map((link) => {
            const active = pathname === link.href || (link.href !== "/" && pathname?.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-accent/10 text-accent-dark"
                    : "text-ink/60 hover:bg-ink/5 hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
