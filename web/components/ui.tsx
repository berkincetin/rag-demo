"use client";

/** Small shared primitives. Everything reads theme tokens from globals.css. */

import { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border bg-[var(--surface)] shadow-[var(--shadow)] ${className}`}
    >
      {children}
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "default",
  disabled,
  type = "button",
  className = "",
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "default" | "primary" | "danger" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
  title?: string;
}) {
  const styles = {
    primary:
      "bg-[var(--accent)] text-[var(--accent-fg)] hover:opacity-90 border-transparent",
    danger:
      "bg-[var(--danger-soft)] text-[var(--danger)] hover:brightness-95 border-transparent",
    ghost: "bg-transparent hover:bg-[var(--surface-2)]",
    default: "bg-[var(--surface)] hover:bg-[var(--surface-2)]",
  }[variant];

  return (
    <button
      type={type}
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg border px-3 py-1.5
        text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-45
        focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]
        ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

export function Badge({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "danger" | "accent";
  title?: string;
}) {
  const styles = {
    neutral: "bg-[var(--surface-2)] text-[var(--text-dim)]",
    ok: "bg-[var(--ok-soft)] text-[var(--ok)]",
    warn: "bg-[var(--warn-soft)] text-[var(--warn)]",
    danger: "bg-[var(--danger-soft)] text-[var(--danger)]",
    accent: "bg-[var(--accent-soft)] text-[var(--accent)]",
  }[tone];

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-0.5
        text-[11px] font-medium ${styles}`}
    >
      {children}
    </span>
  );
}

export function Input({
  value,
  onChange,
  placeholder,
  type = "text",
  label,
  hint,
  onEnter,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  label?: string;
  hint?: string;
  onEnter?: () => void;
}) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-xs font-medium text-[var(--text-dim)]">
          {label}
        </span>
      )}
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && onEnter) onEnter();
        }}
        className="w-full rounded-lg border bg-[var(--surface)] px-3 py-2 text-sm
          outline-none transition placeholder:text-[var(--text-dim)]
          focus:border-[var(--accent)]"
      />
      {hint && <span className="mt-1 block text-[11px] text-[var(--text-dim)]">{hint}</span>}
    </label>
  );
}

export function Select({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  label?: string;
}) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-xs font-medium text-[var(--text-dim)]">
          {label}
        </span>
      )}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border bg-[var(--surface)] px-3 py-2 text-sm
          outline-none transition focus:border-[var(--accent)]"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="px-1 py-3 text-sm text-[var(--text-dim)]">{children}</p>
  );
}

export function SectionTitle({
  children,
  right,
}: {
  children: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="mb-2 flex items-center justify-between gap-3">
      <h2 className="text-sm font-semibold">{children}</h2>
      {right}
    </div>
  );
}

/** Scrolls horizontally on its own so the page body never does. */
export function TableWrap({ children }: { children: ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

export function Th({ children }: { children: ReactNode }) {
  return (
    <th className="whitespace-nowrap border-b px-3 py-2 text-left text-[11px]
      font-semibold uppercase tracking-wide text-[var(--text-dim)]">
      {children}
    </th>
  );
}

export function Td({
  children,
  mono,
}: {
  children: ReactNode;
  mono?: boolean;
}) {
  return (
    <td
      className={`whitespace-nowrap border-b px-3 py-2 text-sm ${
        mono ? "font-mono text-xs" : ""
      }`}
    >
      {children}
    </td>
  );
}
