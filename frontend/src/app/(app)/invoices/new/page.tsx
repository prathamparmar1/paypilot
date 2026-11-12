"use client";
import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { InvoicePreview } from "@/components/invoices/InvoicePreview";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { AIParseResult, CustomerSummary, Invoice } from "@/types";

const EXAMPLE = "Create an invoice for Rahul for $20 for haircut and grooming services, due in 5 days";

export default function NewInvoicePage() {
  const { token, business } = useAuth();
  const router = useRouter();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [form, setForm] = useState({ customer_name: "", customer_email: "", description: "", amount: "", due_date: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState("");

  // AI state
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [ai, setAi] = useState<AIParseResult | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState("");

  useEffect(() => {
    api<CustomerSummary[]>("/customers", {}, token!).then(setCustomers).catch(() => {});
  }, [token]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const today = new Date().toISOString().split("T")[0];

  const runParse = async (parts: string[]) => {
    setAiBusy(true);
    setAiError("");
    try {
      const res = await api<AIParseResult>(
        "/ai/invoice/parse",
        { method: "POST", body: JSON.stringify({ text: parts.join(". ") }) },
        token!
      );
      setHistory(parts);
      setAi(res);
      setAnswer("");
      setForm((f) => ({
        customer_name: res.draft.customer_name ?? f.customer_name,
        customer_email: res.draft.customer_email ?? f.customer_email,
        description: res.draft.description ?? f.description,
        amount: res.draft.amount ?? f.amount,
        due_date: res.draft.due_date ?? f.due_date,
      }));
    } catch (e) {
      setAiError(e instanceof Error ? e.message : "AI request failed");
    } finally {
      setAiBusy(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const intent = ((e.nativeEvent as SubmitEvent).submitter as HTMLElement | null)?.dataset.intent;
    const send = intent === "send";
    setError("");
    setSaving(intent ?? "draft");
    try {
      const inv = await api<Invoice>(
        "/ai/invoice/confirm",
        {
          method: "POST",
          body: JSON.stringify({
            customer_name: form.customer_name,
            customer_email: form.customer_email || null,
            description: form.description,
            amount: form.amount,
            due_date: form.due_date,
            send,
          }),
        },
        token!
      );
      router.replace(`/invoices/${inv.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create invoice");
      setSaving("");
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">New invoice</h1>

      <section className="rounded-2xl border border-blue-100 bg-blue-50/50 p-5">
        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-900">
          <Sparkles className="h-4 w-4 text-brand" /> Describe your invoice
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={2}
          placeholder={EXAMPLE}
          className="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button type="button" loading={aiBusy && history.length === 0} disabled={prompt.trim().length < 3} onClick={() => runParse([prompt.trim()])}>
            Generate with AI
          </Button>
          <button type="button" className="text-xs text-slate-500 hover:underline" onClick={() => setPrompt(EXAMPLE)}>
            Use example
          </button>
        </div>

        {aiError && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{aiError}</p>}

        {ai?.status === "needs_clarification" && (
          <div className="mt-4 space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm text-amber-900">{ai.question}</p>
            <div className="flex gap-2">
              <input
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Your answer…"
                className="flex-1 rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand"
              />
              <Button type="button" loading={aiBusy} disabled={!answer.trim()} onClick={() => runParse([...history, answer.trim()])}>
                Send
              </Button>
            </div>
            <p className="text-xs text-amber-800">You can also fill the missing fields directly in the form below.</p>
          </div>
        )}

        {ai?.status === "ready" && (
          <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            Draft ready. Please review the details below before saving; nothing has been created yet.
          </p>
        )}

        {ai && ai.similar_customers.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
            Existing customer?
            {ai.similar_customers.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setForm((f) => ({ ...f, customer_name: c.name }))}
                className="rounded-full bg-white px-3 py-1 text-xs font-medium text-brand ring-1 ring-blue-200 hover:bg-blue-50"
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        <form onSubmit={submit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
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
          <div className="flex gap-3">
            <Button type="submit" data-intent="draft" variant="secondary" loading={saving === "draft"} className="flex-1">
              Save as draft
            </Button>
            <Button type="submit" data-intent="send" loading={saving === "send"} className="flex-1">
              Confirm &amp; send
            </Button>
          </div>
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