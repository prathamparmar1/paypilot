import { ShieldCheck, Sparkles, Wallet } from "lucide-react";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-slate-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-2 text-xl font-semibold">
          <Wallet className="h-6 w-6 text-blue-400" /> PayPilot
        </div>
        <div className="space-y-6">
          <h2 className="text-3xl font-semibold leading-tight">
            Get paid faster.
            <br />
            Let AI handle the follow-ups.
          </h2>
          <ul className="space-y-3 text-sm text-slate-300">
            <li className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-blue-400" /> Create invoices in plain language</li>
            <li className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-blue-400" /> Payments verified server-side via PayPal</li>
          </ul>
        </div>
        <p className="text-xs text-slate-500">Built for small businesses and freelancers.</p>
      </div>
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
          <p className="mt-1 mb-6 text-sm text-slate-500">{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  );
}