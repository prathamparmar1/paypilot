"use client";
import { PayPalButtons, PayPalScriptProvider } from "@paypal/react-paypal-js";
import { CheckCircle2, ShieldCheck, Wallet, XCircle } from "lucide-react";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";

interface PublicInvoice {
  business_name: string;
  number: string;
  customer_name: string;
  description: string;
  amount: string;
  currency: string;
  due_date: string;
  status: string;
  display_status: string;
  paypal_client_id: string;
}

function PayContent() {
  const { token } = useParams<{ token: string }>();
  const [inv, setInv] = useState<PublicInvoice | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    api<PublicInvoice>(`/pay/${token}`).then(setInv).catch((e) => setError(e.message));
  }, [token]);

  useEffect(load, [load]);

  if (error)
    return (
      <Shell>
        <div className="text-center">
          <XCircle className="mx-auto h-10 w-10 text-slate-400" />
          <h1 className="mt-3 text-lg font-semibold text-slate-900">Invoice not found</h1>
          <p className="mt-1 text-sm text-slate-500">This payment link is invalid or no longer available.</p>
        </div>
      </Shell>
    );

  if (!inv)
    return (
      <Shell>
        <div className="h-48 animate-pulse rounded-xl bg-slate-100" />
      </Shell>
    );

  return (
    <Shell>
      <p className="text-sm text-slate-500">{inv.business_name}</p>
      <p className="mt-1 text-3xl font-semibold text-slate-900">{formatMoney(inv.amount, inv.currency)}</p>
      <dl className="mt-6 space-y-3 text-sm">
        <Row label="Invoice" value={inv.number} />
        <Row label="Billed to" value={inv.customer_name} />
        <Row label="For" value={inv.description} />
        <Row label="Due" value={formatDate(inv.due_date)} />
      </dl>

      <div className="mt-8 border-t border-slate-100 pt-6">
        {inv.status === "PAID" && (
          <div className="flex items-center gap-3 rounded-xl bg-emerald-50 p-4 text-emerald-800">
            <CheckCircle2 className="h-6 w-6" />
            <div>
              <p className="font-medium">Payment received</p>
              <p className="text-xs">Thank you! This invoice has been paid.</p>
            </div>
          </div>
        )}
        {inv.status === "CANCELLED" && (
          <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">This invoice has been cancelled.</p>
        )}
        {inv.status === "SENT" && (
          <>
            {inv.display_status === "OVERDUE" && (
              <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">This invoice is overdue.</p>
            )}
            <PayPalScriptProvider options={{ clientId: inv.paypal_client_id, currency: inv.currency, intent: "capture" }}>
              <PayPalButtons
                style={{ layout: "vertical", shape: "rect" }}
                createOrder={async () => {
                  setMessage("");
                  const r = await api<{ order_id: string }>(`/pay/${token}/create-order`, { method: "POST" });
                  return r.order_id;
                }}
                onApprove={async (data) => {
                  try {
                    await api(`/pay/${token}/capture`, {
                      method: "POST",
                      body: JSON.stringify({ order_id: data.orderID }),
                    });
                  } catch (e) {
                    setMessage(e instanceof Error ? e.message : "Could not confirm payment.");
                  }
                  load(); // status shown comes from the server, not from this callback
                }}
                onError={() => setMessage("Something went wrong with PayPal. You have not been charged. Please try again.")}
              />
            </PayPalScriptProvider>
            {message && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p>}
          </>
        )}
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 py-10">
      <div className="mb-6 flex items-center gap-2 text-lg font-semibold text-slate-900">
        <Wallet className="h-5 w-5 text-brand" /> PayPilot
      </div>
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">{children}</div>
      <p className="mt-6 flex items-center gap-1.5 text-xs text-slate-400">
        <ShieldCheck className="h-3.5 w-3.5" /> Secure payments powered by PayPal
      </p>
    </main>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-right font-medium text-slate-800">{value}</dd>
    </div>
  );
}
export default function PayPage() {
  return (
    <Suspense
      fallback={
        <Shell>
          <div className="h-48 animate-pulse rounded-xl bg-slate-100" />
        </Shell>
      }
    >
      <PayContent />
    </Suspense>
  );
}