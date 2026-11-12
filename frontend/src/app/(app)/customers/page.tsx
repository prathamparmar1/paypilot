"use client";
import { Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { CustomerSummary } from "@/types";

export default function CustomersPage() {
  const { token } = useAuth();
  const [customers, setCustomers] = useState<CustomerSummary[] | null>(null);
  const [form, setForm] = useState({ name: "", email: "", phone: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api<CustomerSummary[]>("/customers", {}, token!).then(setCustomers).catch((e) => setError(e.message));
  }, [token]);

  useEffect(load, [load]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await api(
        "/customers",
        {
          method: "POST",
          body: JSON.stringify({ name: form.name, email: form.email || null, phone: form.phone || null }),
        },
        token!
      );
      setForm({ name: "", email: "", phone: "" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add customer");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Customers</h1>

      <form onSubmit={onSubmit} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-4 sm:items-end">
        <Input label="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <Button type="submit" loading={saving}>Add customer</Button>
      </form>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {customers === null && !error && <div className="h-40 animate-pulse rounded-xl bg-slate-200/60" />}

      {customers && customers.length === 0 && (
        <EmptyState
          icon={<Users className="h-5 w-5" />}
          title="No customers yet"
          description="Add a customer above, or they'll be created automatically when you make an invoice."
        />
      )}

      {customers && customers.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Contact</th>
                <th className="px-5 py-3 text-right font-medium">Invoices</th>
                <th className="px-5 py-3 text-right font-medium">Paid</th>
                <th className="px-5 py-3 text-right font-medium">Outstanding</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {customers.map((c) => (
                <tr key={c.id}>
                  <td className="px-5 py-3.5 font-medium text-slate-900">{c.name}</td>
                  <td className="px-5 py-3.5 text-slate-500">{c.email || c.phone || "—"}</td>
                  <td className="px-5 py-3.5 text-right">{c.invoice_count}</td>
                  <td className="px-5 py-3.5 text-right text-emerald-700">{formatMoney(c.total_paid)}</td>
                  <td className="px-5 py-3.5 text-right text-slate-900">{formatMoney(c.outstanding)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}