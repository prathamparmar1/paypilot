"use client";
import { Check, Copy, Send, XCircle } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { InvoicePreview } from "@/components/invoices/InvoicePreview";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { Invoice } from "@/types";

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, business } = useAuth();
  const [inv, setInv] = useState<Invoice | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api<Invoice>(`/invoices/${id}`, {}, token!).then(setInv).catch((e) => setError(e.message));
  }, [id, token]);

  const act = async (action: "send" | "cancel") => {
    setBusy(action);
    setError("");
    try {
      setInv(await api<Invoice>(`/invoices/${id}/${action}`, { method: "POST" }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy("");
    }
  };

  if (error && !inv) return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  if (!inv) return <div className="h-64 animate-pulse rounded-xl bg-slate-200/60" />;

  const payLink = typeof window !== "undefined" ? `${window.location.origin}/pay/${inv.public_token}` : "";
  const canSend = inv.status === "DRAFT";
  const canCancel = inv.status === "DRAFT" || inv.status === "SENT";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">{inv.number}</h1>
        <div className="flex gap-2">
          {canSend && (
            <Button loading={busy === "send"} onClick={() => act("send")}>
              <Send className="h-4 w-4" /> Send invoice
            </Button>
          )}
          {canCancel && (
            <Button variant="secondary" loading={busy === "cancel"} onClick={() => act("cancel")}>
              <XCircle className="h-4 w-4" /> Cancel
            </Button>
          )}
        </div>
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <InvoicePreview
        number={inv.number}
        businessName={business?.business_name ?? ""}
        customerName={inv.customer_name}
        description={inv.description}
        amount={inv.amount}
        dueDate={inv.due_date}
        status={inv.display_status}
      />

      {inv.status === "SENT" && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-sm font-medium text-slate-900">Payment link</p>
          <p className="mt-0.5 text-xs text-slate-500">Share this with your customer (payment page arrives in Phase 6).</p>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 truncate rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-700">{payLink}</code>
            <Button
              variant="secondary"
              onClick={() => {
                navigator.clipboard.writeText(payLink);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}