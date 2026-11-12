"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Home() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    api<{ status: string }>("/health")
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="rounded-xl border bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">PayPilot</h1>
        <p className="mt-2 text-sm text-slate-600">API status: {status}</p>
      </div>
    </main>
  );
}