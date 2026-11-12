"use client";
import clsx from "clsx";
import { Bell, Check, Copy, RefreshCw, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type { Reminder, ReminderCandidate } from "@/types";

type Tab = "needs" | "drafts" | "history";

export default function RemindersPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<Tab>("needs");
  const [cands, setCands] = useState<ReminderCandidate[] | null>(null);
  const [rems, setRems] = useState<Reminder[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    try {
      const [c, r] = await Promise.all([
        api<ReminderCandidate[]>("/reminders/candidates", {}, token!),
        api<Reminder[]>("/reminders", {}, token!),
      ]);
      setCands(c);
      setRems(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (key: string, fn: () => Promise<unknown>, next?: Tab) => {
    setBusy(key);
    setError("");
    try {
      await fn();
      await load();
      if (next) setTab(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy("");
    }
  };

  const drafts = rems?.filter((r) => r.status === "DRAFT") ?? [];
  const history = rems?.filter((r) => r.status !== "DRAFT") ?? [];
  const tabs: { id: Tab; label: string; n: number }[] = [
    { id: "needs", label: "Needs reminder", n: cands?.filter((c) => !c.has_draft).length ?? 0 },
    { id: "drafts", label: "Drafts", n: drafts.length },
    { id: "history", label: "History", n: history.length },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Payment reminders</h1>
        <p className="text-sm text-slate-500">AI drafts a message. You review and approve it before anything is used.</p>
      </div>

      <div className="flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              "rounded-full px-3.5 py-1.5 text-sm font-medium",
              tab === t.id ? "bg-slate-900 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
            )}
          >
            {t.label} <span className="opacity-60">{t.n}</span>
          </button>
        ))}
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {(cands === null || rems === null) && !error && <div className="h-40 animate-pulse rounded-xl bg-slate-200/60" />}

      {cands && tab === "needs" && (
        cands.length === 0 ? (
          <EmptyState icon={<Bell className="h-5 w-5" />} title="Nothing to chase" description="Unpaid sent invoices will appear here." />
        ) : (
          <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
            {cands.map((c) => (
              <div key={c.invoice_id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {c.customer_name} <span className="text-slate-400">· {c.number}</span>
                  </p>
                  <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
                    <StatusBadge status={c.display_status} />
                    {formatMoney(c.amount, c.currency)} · due {formatDate(c.due_date)}
                    {c.days_overdue > 0 && ` · ${c.days_overdue}d overdue`}
                    {c.last_reminded_at && ` · last reminded ${formatDate(c.last_reminded_at)}`}
                  </p>
                </div>
                {c.has_draft ? (
                  <Button variant="secondary" onClick={() => setTab("drafts")}>View draft</Button>
                ) : (
                  <Button
                    loading={busy === c.invoice_id}
                    onClick={() => run(c.invoice_id, () => api(`/reminders/generate/${c.invoice_id}`, { method: "POST" }, token!), "drafts")}
                  >
                    <Sparkles className="h-4 w-4" /> Draft reminder
                  </Button>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {rems && tab === "drafts" && (
        drafts.length === 0 ? (
          <EmptyState icon={<Bell className="h-5 w-5" />} title="No drafts" description="Generate a reminder from the first tab." />
        ) : (
          <div className="space-y-4">
            {drafts.map((r) => (
              <DraftCard key={r.id} r={r} busy={busy} onRun={run} token={token!} />
            ))}
          </div>
        )
      )}

      {rems && tab === "history" && (
        history.length === 0 ? (
          <EmptyState icon={<Bell className="h-5 w-5" />} title="No history yet" description="Approved and dismissed reminders show up here." />
        ) : (
          <div className="space-y-3">
            {history.map((r) => (
              <div key={r.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between text-sm">
                  <p className="font-medium text-slate-900">
                    {r.customer_name} <span className="text-slate-400">· {r.invoice_number}</span>
                  </p>
                  <span className={clsx("rounded-full px-2.5 py-0.5 text-xs font-medium", r.status === "APPROVED" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500")}>
                    {r.status === "APPROVED" ? `Approved ${r.approved_at ? formatDate(r.approved_at) : ""}` : "Dismissed"}
                  </span>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{r.message}</p>
                {r.status === "APPROVED" && (
                  <button
                    onClick={() => navigator.clipboard.writeText(r.message)}
                    className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand hover:underline"
                  >
                    <Copy className="h-3.5 w-3.5" /> Copy message
                  </button>
                )}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}

function DraftCard({
  r, busy, onRun, token,
}: {
  r: Reminder;
  busy: string;
  onRun: (key: string, fn: () => Promise<unknown>, next?: Tab) => Promise<void>;
  token: string;
}) {
  const [text, setText] = useState(r.message);
  useEffect(() => setText(r.message), [r.message]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-medium text-slate-900">
          {r.customer_name} <span className="text-slate-400">· {r.invoice_number} · {formatMoney(r.amount, r.currency)}</span>
        </p>
        <StatusBadge status={r.invoice_status} />
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={7}
        className="w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          loading={busy === `a${r.id}`}
          onClick={() =>
            onRun(`a${r.id}`, async () => {
              if (text.trim() !== r.message) {
                await api(`/reminders/${r.id}`, { method: "PATCH", body: JSON.stringify({ message: text }) }, token);
              }
              await api(`/reminders/${r.id}/approve`, { method: "POST" }, token);
            }, "history")
          }
        >
          <Check className="h-4 w-4" /> Approve
        </Button>
        <Button
          variant="secondary"
          loading={busy === `g${r.id}`}
          onClick={() => onRun(`g${r.id}`, () => api(`/reminders/generate/${r.invoice_id}`, { method: "POST" }, token))}
        >
          <RefreshCw className="h-4 w-4" /> Regenerate
        </Button>
        <Button variant="ghost" loading={busy === `d${r.id}`} onClick={() => onRun(`d${r.id}`, () => api(`/reminders/${r.id}/dismiss`, { method: "POST" }, token))}>
          <X className="h-4 w-4" /> Dismiss
        </Button>
      </div>
    </div>
  );
}