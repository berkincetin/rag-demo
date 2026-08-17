"use client";

import Link from "next/link";
import { useState } from "react";

import { groupByDate } from "@/lib/storage";
import { Conversation } from "@/lib/types";
import ConversationItem from "./ConversationItem";
import SettingsMenu from "./SettingsMenu";

export default function Sidebar({
  conversations,
  activeId,
  collapsed,
  dark,
  onToggleCollapse,
  onToggleTheme,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onSignOut,
}: {
  conversations: Conversation[];
  activeId: string | null;
  collapsed: boolean;
  dark: boolean;
  onToggleCollapse: () => void;
  onToggleTheme: () => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onSignOut: () => void;
}) {
  const [query, setQuery] = useState("");

  const needle = query.trim().toLocaleLowerCase("tr");
  const filtered = needle
    ? conversations.filter((c) => c.title.toLocaleLowerCase("tr").includes(needle))
    : conversations;

  const groups = groupByDate([...filtered].sort((a, b) => b.updatedAt - a.updatedAt));

  return (
    <aside
      className={`flex h-full flex-col border-r border-[var(--border)] bg-[var(--surface)]
        transition-all duration-200 ${collapsed ? "w-14" : "w-64"}`}
    >
      <div className="flex items-center gap-1 p-2">
        <button
          onClick={onToggleCollapse}
          title={collapsed ? "Genişlet" : "Daralt"}
          className="rounded-lg p-2 text-[var(--text-dim)] transition-colors
            hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <path d="M3 6h18M3 12h18M3 18h18" />
          </svg>
        </button>
        {!collapsed && <span className="text-sm font-semibold">Bilgi Asistanı</span>}
      </div>

      <div className={collapsed ? "px-2" : "px-2 pb-2"}>
        <button
          onClick={onNew}
          title="Yeni sohbet"
          className={`flex items-center justify-center gap-2 rounded-lg bg-[var(--accent)] py-2
            text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90
            ${collapsed ? "w-10" : "w-full"}`}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
          {!collapsed && "Yeni sohbet"}
        </button>
      </div>

      {!collapsed && (
        <div className="px-2 pb-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Sohbetlerde ara"
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5
              text-sm text-[var(--text)] outline-none placeholder:text-[var(--text-dim)]
              focus:border-[var(--accent)]"
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-2">
        {groups.length === 0 && !collapsed && (
          <p className="px-2 py-4 text-xs text-[var(--text-dim)]">Sohbet bulunamadı.</p>
        )}
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            {!collapsed && (
              <div
                className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider
                  text-[var(--text-dim)]"
              >
                {group.label}
              </div>
            )}
            <div className="flex flex-col gap-0.5">
              {group.items.map((conversation) => (
                <ConversationItem
                  key={conversation.id}
                  conversation={conversation}
                  active={conversation.id === activeId}
                  collapsed={collapsed}
                  onSelect={() => onSelect(conversation.id)}
                  onRename={(title) => onRename(conversation.id, title)}
                  onDelete={() => onDelete(conversation.id)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-1 border-t border-[var(--border)] p-2">
        <SettingsMenu collapsed={collapsed} />
        <Link
          href="/analiz"
          title="Bölüm 2 analizi"
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--text-dim)]
            transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]
            ${collapsed ? "justify-center px-0" : ""}`}
        >
          📊 {!collapsed && "Satış analizi"}
        </Link>
        <button
          onClick={onToggleTheme}
          title={dark ? "Açık tema" : "Koyu tema"}
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--text-dim)]
            transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]
            ${collapsed ? "justify-center px-0" : ""}`}
        >
          {dark ? "☀️" : "🌙"} {!collapsed && (dark ? "Açık tema" : "Koyu tema")}
        </button>
        <button
          onClick={onSignOut}
          title="Çıkış yap"
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--text-dim)]
            transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]
            ${collapsed ? "justify-center px-0" : ""}`}
        >
          🚪 {!collapsed && "Çıkış yap"}
        </button>
      </div>
    </aside>
  );
}
