import messages from "@/data/messages.json";
import type { ChatMessage } from "@/types";
import { wait } from "@/utils";

const replies = messages.replies as Record<
  string,
  { content: string; sources: string[] }
>;

export async function sendMessage(
  question: string,
  history: ChatMessage[],
): Promise<ChatMessage> {
  await wait(800);
  const match = replies[question.trim()] ?? messages.fallback;
  return {
    id: `ai-${history.length + 1}`,
    role: "assistant",
    content: match.content,
    sources: match.sources,
  };
}

export function getSuggestedQuestions() {
  return messages.suggestedQuestions;
}
