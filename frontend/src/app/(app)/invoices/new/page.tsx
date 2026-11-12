"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { InvoicePreview } from "@/components/invoices/InvoicePreview";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { CustomerSummary, Invoice } from "@/types";

export default function NewInvoicePage() {
  const { token, business } = useAuth();
  const router = useRouter();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [form, setForm] = useState({ customer_name: "", customer_email: "", description: "", amount: "", due_date: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api<CustomerSummary[]>("/customers", {}, token!).then(setCustomers).catch(() => {});
  }, [token]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const today = new Date().toISOString().split("T")[0];

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const inv = await api<Invoice>(
        "/invoices",
        {
          method: "POST",
          body: JSON.stringify({
            customer_name: form.customer_name,
            customer_email: form.customer_email || null,
            description: form.description,
            amount: form.amount,
            due_date: form.due_date,
          }),
        },
        token!
      );
      router.replace(`/invoices/${inv.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create invoice");
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">New invoice</h1>
      <div className="grid gap-8 lg:grid-cols-2">
        <form onSubmit={onSubmit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
          <Input label="Customer name" required list="customer-list" value={form.customer_name} onChange={set("customer_name")} />
          <datalist id="customer-list">
            {customers.map((c) => <option key={c.id} value={c.name} />)}
          </datalist>
          <Input label="Customer email (optional)" type="email" value={form.customer_email} onChange={set("customer_email")} />
          <Input label="Description" required minLength={3} value={form.description} onChange={set("description")} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Amount (USD)" type="number" required min="0.01" step="0.01" value={form.amount} onChange={set("amount")} />
            <Input label="Due date" type="date" required min={today} value={form.due_date} onChange={set("due_date")} />
          </div>
          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <Button type="submit" loading={saving} className="w-full">Save as draft</Button>
        </form>

        <InvoicePreview
          businessName={business?.business_name ?? ""}
          customerName={form.customer_name}
          description={form.description}
          amount={form.amount}
          dueDate={form.due_date}
          status="DRAFT"
        />
      </div>
    </div>
  );
}