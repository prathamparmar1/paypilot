"use client";
import clsx from "clsx";
import { Check, Loader2, SendHorizonal, Sparkles, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { ChatMessage, PendingActionOut } from "@/types";

const SUGGESTIONS = [
  "How much revenue did I generate this month?",
  "Show me all overdue invoices.",
  "Which customers have pending payments?",
  "How much money is outstanding?",
  "Show my five largest transactions.",
];

export default function AssistantPage() {
  const { token } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState<PendingActionOut[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<{ messages: ChatMessage[]; pending_actions: PendingActionOut[] }>("/ai/chat/history", {}, token!)
      .then((h) => {
        setMessages(h.messages);
        setPending(h.pending_actions);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoaded(true));
  }, [token]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending, busy]);

  const send = useCallback(
    async (text: string) => {
      const msg = text.trim();
      if (!msg || busy) return;
      setError("");
      setInput("");
      setMessages((m) => [...m, { role: "user", content: msg }]);
      setBusy(true);
      try {
        const res = await api<{ reply: string; pending_actions: PendingActionOut[] }>(
          "/ai/chat",
          { method: "POST", body: JSON.stringify({ message: msg }) },
          token!
        );
        setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
        if (res.pending_actions.length) {
          setPending((p) => [...p.filter((x) => !res.pending_actions.some((n) => n.id === x.id)), ...res.pending_actions]);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong");
      } finally {
        setBusy(false);
      }
    },
    [busy, token]
  );

  const decide = async (id: string, kind: "confirm" | "cancel") => {
    setActionBusy(id);
    setError("");
    try {
      const res = await api<{ message: string }>(`/ai/actions/${id}/${kind}`, { method: "POST" }, token!);
      setMessages((m) => [...m, { role: "assistant", content: res.message }]);
      setPending((p) => p.filter((x) => x.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
      setPending((p) => p.filter((x) => x.id !== id));
    } finally {
      setActionBusy("");
    }
  };

  const clear = async () => {
    await api("/ai/chat/history", { method: "DELETE" }, token!).catch(() => {});
    setMessages([]);
  };

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">AI Assistant</h1>
          <p className="text-sm text-slate-500">Ask about your invoices, payments and customers.</p>
        </div>
        {messages.length > 0 && (
          <button onClick={clear} className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-100">
            <Trash2 className="h-4 w-4" /> Clear
          </button>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5">
        {loaded && messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-3 rounded-full bg-blue-50 p-3 text-brand"><Sparkles className="h-5 w-5" /></div>
            <p className="mb-4 text-sm text-slate-500">Try one of these:</p>
            <div className="flex max-w-xl flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} className="rounded-full bg-slate-50 px-3.5 py-2 text-sm text-slate-700 ring-1 ring-slate-200 hover:bg-slate-100">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={clsx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div
              className={clsx(
                "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                m.role === "user" ? "bg-brand text-white" : "bg-slate-100 text-slate-900"
              )}
            >
              {m.content}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
          </div>
        )}

        {pending.map((p) => (
          <div key={p.id} className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-amber-700">Confirmation required</p>
            <p className="mt-1 text-sm font-medium text-slate-900">{p.summary}</p>
            <div className="mt-3 flex gap-2">
              <button
                disabled={actionBusy === p.id}
                onClick={() => decide(p.id, "confirm")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-60"
              >
                <Check className="h-4 w-4" /> Confirm
              </button>
              <button
                disabled={actionBusy === p.id}
                onClick={() => decide(p.id, "cancel")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3.5 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 disabled:opacity-60"
              >
                <X className="h-4 w-4" /> Cancel
              </button>
            </div>
          </div>
        ))}
        <div ref={bottom} />
      </div>

      {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          maxLength={1000}
          placeholder="Ask about your payments…"
          className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="inline-flex items-center justify-center rounded-xl bg-brand px-4 text-white hover:bg-brand-dark disabled:opacity-60"
          aria-label="Send"
        >
          <SendHorizonal className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}