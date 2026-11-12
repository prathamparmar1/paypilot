"use client";
import clsx from "clsx";
import { FileText, Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type { Invoice } from "@/types";

const filters = [
  { label: "All", value: "" },
  { label: "Draft", value: "DRAFT" },
  { label: "Pending", value: "PENDING" },
  { label: "Overdue", value: "OVERDUE" },
  { label: "Paid", value: "PAID" },
  { label: "Cancelled", value: "CANCELLED" },
];

export default function InvoicesPage() {
  const { token } = useAuth();
  const [filter, setFilter] = useState("");
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setInvoices(null);
    setError("");
    api<Invoice[]>(`/invoices${filter ? `?status=${filter}` : ""}`, {}, token!)
      .then(setInvoices)
      .catch((e) => setError(e.message));
  }, [filter, token]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Invoices</h1>
        <Link href="/invoices/new">
          <Button><Plus className="h-4 w-4" /> New invoice</Button>
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={clsx(
              "rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors",
              filter === f.value ? "bg-slate-900 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {invoices === null && !error && <div className="h-40 animate-pulse rounded-xl bg-slate-200/60" />}

      {invoices && invoices.length === 0 && (
        <EmptyState
          icon={<FileText className="h-5 w-5" />}
          title="No invoices found"
          description="Create your first invoice to start getting paid."
          action={<Link href="/invoices/new"><Button>Create invoice</Button></Link>}
        />
      )}

      {invoices && invoices.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-5 py-3 font-medium">Invoice</th>
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Due</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3.5 font-medium">
                    <Link href={`/invoices/${inv.id}`} className="text-brand hover:underline">{inv.number}</Link>
                  </td>
                  <td className="px-5 py-3.5 text-slate-700">{inv.customer_name}</td>
                  <td className="px-5 py-3.5 text-slate-500">{formatDate(inv.due_date)}</td>
                  <td className="px-5 py-3.5"><StatusBadge status={inv.display_status} /></td>
                  <td className="px-5 py-3.5 text-right font-medium text-slate-900">{formatMoney(inv.amount, inv.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}