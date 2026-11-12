"use client";
import { AlertCircle, CheckCircle2, Clock, DollarSign, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type { DashboardSummary } from "@/types";
import { InsightsPanel } from "@/components/dashboard/InsightsPanel";

export default function DashboardPage() {
  const { business, token } = useAuth();
  const [s, setS] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<DashboardSummary>("/dashboard/summary", {}, token!).then(setS).catch((e) => setError(e.message));
  }, [token]);

  const cards = [
    { label: "Total revenue", value: s && formatMoney(s.total_revenue), sub: "Verified payments", icon: DollarSign, tone: "text-emerald-600 bg-emerald-50" },
    { label: "Pending payments", value: s && formatMoney(s.pending_amount), sub: s && `${s.pending_count} unpaid invoices`, icon: Clock, tone: "text-blue-600 bg-blue-50" },
    { label: "Paid invoices", value: s && String(s.paid_count), sub: "Confirmed by PayPal", icon: CheckCircle2, tone: "text-emerald-600 bg-emerald-50" },
    { label: "Overdue", value: s && formatMoney(s.overdue_amount), sub: s && `${s.overdue_count} invoices`, icon: AlertCircle, tone: "text-red-600 bg-red-50" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Hello, {business?.owner_name.split(" ")[0]}</h1>
        <p className="text-sm text-slate-500">Here&apos;s an overview of {business?.business_name}.</p>
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ label, value, sub, icon: Icon, tone }) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-5">
            <div className={`mb-3 inline-flex rounded-lg p-2 ${tone}`}><Icon className="h-4 w-4" /></div>
            <p className="text-sm text-slate-500">{label}</p>
            {value ? (
              <>
                <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
                <p className="text-xs text-slate-400">{sub}</p>
              </>
            ) : (
              <div className="mt-2 h-8 w-24 animate-pulse rounded bg-slate-200/70" />
            )}
          </div>
        ))}
      </div>
      
      <InsightsPanel />

      <section>
        <h2 className="mb-3 text-base font-semibold text-slate-900">Recent transactions</h2>
        {s && s.recent_payments.length === 0 && (
          <EmptyState
            icon={<FileText className="h-5 w-5" />}
            title="No transactions yet"
            description="Verified payments will appear here once customers pay their invoices."
          />
        )}
        {s && s.recent_payments.length > 0 && (
          <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
            {s.recent_payments.map((p) => (
              <div key={p.id} className="flex items-center justify-between px-5 py-3.5 text-sm">
                <div>
                  <p className="font-medium text-slate-900">{p.customer_name}</p>
                  <p className="text-xs text-slate-500">{p.invoice_number} · {formatDate(p.verified_at)}</p>
                </div>
                <p className="font-semibold text-emerald-700">+{formatMoney(p.amount, p.currency)}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}