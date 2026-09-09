export function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl bg-blue-600 px-4 py-3 text-sm text-white">
        {content}
      </div>
    </div>
  );
}

export function SourceBadge({ sources }: { sources: string[] }) {
  if (!sources.length) return null;
  return (
    <span className="mt-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
      Sources: {sources.join(" + ")}
    </span>
  );
}

export function AIMessage({
  content,
  sources = [],
}: {
  content: string;
  sources?: string[];
}) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-800">
        <p className="whitespace-pre-line">{content}</p>
        <SourceBadge sources={sources} />
      </div>
    </div>
  );
}

export function ChatMessage({
  role,
  content,
  sources,
}: {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}) {
  if (role === "user") return <UserMessage content={content} />;
  return <AIMessage content={content} sources={sources} />;
}
