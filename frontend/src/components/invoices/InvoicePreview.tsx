import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate, formatMoney } from "@/lib/format";

interface Props {
  number?: string;
  businessName: string;
  customerName: string;
  description: string;
  amount: string | number;
  dueDate: string;
  status?: string;
}

export function InvoicePreview({ number, businessName, customerName, description, amount, dueDate, status }: Props) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Invoice</p>
          <p className="text-lg font-semibold text-slate-900">{number ?? "Preview"}</p>
        </div>
        {status && <StatusBadge status={status} />}
      </div>

      <div className="mt-8 grid grid-cols-2 gap-6 text-sm">
        <div>
          <p className="text-slate-400">From</p>
          <p className="mt-1 font-medium text-slate-900">{businessName}</p>
        </div>
        <div>
          <p className="text-slate-400">Billed to</p>
          <p className="mt-1 font-medium text-slate-900">{customerName || "—"}</p>
        </div>
        <div>
          <p className="text-slate-400">Due date</p>
          <p className="mt-1 font-medium text-slate-900">{dueDate ? formatDate(dueDate) : "—"}</p>
        </div>
      </div>

      <div className="mt-8 border-t border-slate-100 pt-6">
        <p className="text-sm text-slate-400">Description</p>
        <p className="mt-1 text-sm text-slate-800">{description || "—"}</p>
      </div>

      <div className="mt-8 flex items-center justify-between rounded-xl bg-slate-50 px-5 py-4">
        <span className="text-sm text-slate-500">Amount due</span>
        <span className="text-2xl font-semibold text-slate-900">
          {amount === "" || Number.isNaN(Number(amount)) ? "—" : formatMoney(amount)}
        </span>
      </div>
    </div>
  );
}