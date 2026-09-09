"use client";

import { ChatMessage } from "@/components/chat/ChatMessage";
import { AppShell } from "@/components/layout/AppShell";
import { getSuggestedQuestions, sendMessage } from "@/services/api/assistant.service";
import type { ChatMessage as ChatMessageType } from "@/types";
import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { FormEvent, useRef, useState } from "react";

export default function AssistantPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessageType[]>([
    {
      id: "seed-user",
      role: "user",
      content: "What needs my attention this month?",
    },
    {
      id: "seed-ai",
      role: "assistant",
      content:
        "You have 2 important items this month:\n\n1. Electricity bill — ₹4,850 due on 18 September.\n2. Car insurance — renewal coming up on 12 October.",
      sources: ["BESCOM bill", "Car insurance policy"],
    },
  ]);
  const endRef = useRef<HTMLDivElement>(null);
  const suggestions = getSuggestedQuestions();

  const mutation = useMutation({
    mutationFn: (question: string) => sendMessage(question, messages),
    onSuccess: (reply) => {
      setMessages((current) => [...current, reply]);
      window.setTimeout(
        () => endRef.current?.scrollIntoView({ behavior: "smooth" }),
        50,
      );
    },
  });

  function submit(question: string) {
    const trimmed = question.trim();
    if (!trimmed || mutation.isPending) return;
    setInput("");
    setMessages((current) => [
      ...current,
      { id: `user-${current.length}`, role: "user", content: trimmed },
    ]);
    mutation.mutate(trimmed);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit(input);
  }

  return (
    <AppShell>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section className="flex min-h-[520px] flex-col rounded-2xl border border-slate-200 bg-white p-4 md:p-6">
          <div className="flex-1 space-y-4 overflow-y-auto">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                sources={message.sources}
              />
            ))}
            {mutation.isPending ? (
              <p className="text-sm text-slate-400">Thinking…</p>
            ) : null}
            <div ref={endRef} />
          </div>
          <form onSubmit={onSubmit} className="mt-4 flex gap-2">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about your bills, policies, warranties..."
              className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded-xl bg-blue-600 p-3 text-white hover:bg-blue-700 disabled:bg-blue-300"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </section>
        <aside className="rounded-2xl bg-[#0b1b33] p-5 text-white">
          <h2 className="font-semibold">Try asking</h2>
          <div className="mt-4 space-y-3">
            {suggestions.map((question) => (
              <button
                key={question}
                type="button"
                onClick={() => setInput(question)}
                className="w-full rounded-xl border border-white/10 bg-[#12243f] px-4 py-3 text-left text-sm hover:bg-[#173056]"
              >
                {question}
              </button>
            ))}
          </div>
        </aside>
      </div>
    </AppShell>
  );
}
