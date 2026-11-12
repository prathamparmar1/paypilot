"use client";
import { AlertCircle, CheckCircle2, Clock, DollarSign, FileText } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/context/AuthContext";

const stats = [
  { label: "Total revenue", icon: DollarSign, tone: "text-emerald-600 bg-emerald-50" },
  { label: "Pending payments", icon: Clock, tone: "text-blue-600 bg-blue-50" },
  { label: "Paid invoices", icon: CheckCircle2, tone: "text-emerald-600 bg-emerald-50" },
  { label: "Overdue invoices", icon: AlertCircle, tone: "text-red-600 bg-red-50" },
];

export default function DashboardPage() {
  const { business } = useAuth();
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Hello, {business?.owner_name.split(" ")[0]}</h1>
        <p className="text-sm text-slate-500">Here&apos;s an overview of {business?.business_name}.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(({ label, icon: Icon, tone }) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-5">
            <div className={`mb-3 inline-flex rounded-lg p-2 ${tone}`}>
              <Icon className="h-4 w-4" />
            </div>
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">—</p>
          </div>
        ))}
      </div>

      <section>
        <h2 className="mb-3 text-base font-semibold text-slate-900">Recent transactions</h2>
        <EmptyState
          icon={<FileText className="h-5 w-5" />}
          title="No transactions yet"
          description="Once you create invoices and customers pay them, verified payments will appear here."
        />
      </section>
    </div>
  );
}