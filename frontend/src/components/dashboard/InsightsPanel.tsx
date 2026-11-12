"use client";
import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { InsightsResponse } from "@/types";

export function InsightsPanel() {
  const { token } = useAuth();
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api<InsightsResponse>("/insights", {}, token!).then(setData).catch(() => setFailed(true));
  }, [token]);

  if (failed) return null;
  if (!data) return <div className="h-56 animate-pulse rounded-xl bg-slate-200/60" />;

  const months = data.stats.monthly_revenue;
  const max = Math.max(...months.map((m) => Number(m.revenue_usd)), 1);
  const aging = data.stats.overdue_aging.filter((a) => a.count > 0);

  return (
    <section className="grid gap-4 lg:grid-cols-5">
      <div className="rounded-xl border border-slate-200 bg-white p-5 lg:col-span-3">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-brand" />
          <h2 className="text-base font-semibold text-slate-900">Business insights</h2>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
            {data.ai_generated ? "AI · from your data" : "From your data"}
          </span>
        </div>
        <ul className="space-y-2.5 text-sm text-slate-700">
          {data.insights.map((s, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
              {s}
            </li>
          ))}
        </ul>
        {aging.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
            {aging.map((a) => (
              <span key={a.bucket} className="rounded-lg bg-red-50 px-3 py-1.5 text-xs text-red-700">
                Overdue {a.bucket}: {a.count} · {formatMoney(a.amount_usd)}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 lg:col-span-2">
        <h2 className="mb-4 text-base font-semibold text-slate-900">Monthly revenue</h2>
        <div className="flex h-32 items-end gap-2">
          {months.map((m) => (
            <div key={m.label} className="flex flex-1 flex-col items-center gap-1.5" title={`${m.label}: ${formatMoney(m.revenue_usd)}`}>
              <div className="flex h-full w-full items-end">
                <div
                  className="w-full rounded-t bg-brand/80"
                  style={{ height: `${Math.max((Number(m.revenue_usd) / max) * 100, Number(m.revenue_usd) > 0 ? 4 : 1)}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-400">{m.label.split(" ")[0]}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}