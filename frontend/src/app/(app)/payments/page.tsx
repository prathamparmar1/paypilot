"use client";
import { Receipt } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";

interface Payment {
  id: string;
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  amount: string;
  currency: string;
  status: string;
  paypal_order_id: string;
  paypal_capture_id: string;
  payer_email: string | null;
  verified_at: string;
}

export default function PaymentsPage() {
  const { token } = useAuth();
  const [rows, setRows] = useState<Payment[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Payment[]>("/payments", {}, token!).then(setRows).catch((e) => setError(e.message));
  }, [token]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Payments</h1>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {rows === null && !error && <div className="h-40 animate-pulse rounded-xl bg-slate-200/60" />}
      {rows && rows.length === 0 && (
        <EmptyState
          icon={<Receipt className="h-5 w-5" />}
          title="No payments yet"
          description="PayPal-verified payments will be listed here with their transaction references."
        />
      )}
      {rows && rows.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-5 py-3 font-medium">Date</th>
                <th className="px-5 py-3 font-medium">Invoice</th>
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">PayPal capture ID</th>
                <th className="px-5 py-3 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((p) => (
                <tr key={p.id}>
                  <td className="px-5 py-3.5 text-slate-500">{formatDate(p.verified_at)}</td>
                  <td className="px-5 py-3.5 font-medium">
                    <Link href={`/invoices/${p.invoice_id}`} className="text-brand hover:underline">{p.invoice_number}</Link>
                  </td>
                  <td className="px-5 py-3.5 text-slate-700">
                    {p.customer_name}
                    {p.payer_email && <span className="block text-xs text-slate-400">{p.payer_email}</span>}
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-500">{p.paypal_capture_id}</td>
                  <td className="px-5 py-3.5 text-right font-semibold text-emerald-700">{formatMoney(p.amount, p.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}