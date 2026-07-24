"use client";

import { Share2 } from "lucide-react";
import { useState } from "react";

export function ShareButton() {
  const [copied, setCopied] = useState(false);

  return (
    <button
      className="inline-flex h-9 items-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] font-semibold text-[var(--text-2)]"
      onClick={async () => {
        await navigator.clipboard.writeText(window.location.href);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      }}
      type="button"
    >
      <Share2 aria-hidden="true" className="size-3.5" />
      {copied ? "Link copied" : "Share"}
    </button>
  );
}
