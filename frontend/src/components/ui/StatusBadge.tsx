import clsx from "clsx";

const styles: Record<string, string> = {
  PAID: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  SENT: "bg-blue-50 text-blue-700 ring-blue-600/20",
  DRAFT: "bg-slate-100 text-slate-600 ring-slate-500/20",
  OVERDUE: "bg-red-50 text-red-700 ring-red-600/20",
  CANCELLED: "bg-amber-50 text-amber-700 ring-amber-600/20",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        styles[status] ?? styles.DRAFT
      )}
    >
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </span>
  );
}