import type { AgentStep } from "@/components/conversation-view/agent-steps.tsx";
import type { AiMessageProps, MessageProps } from "@/components/conversation-view/chat-session.tsx";

const isStreamedAnswer = (message: MessageProps | undefined): message is AiMessageProps =>
  !!message && message.type === "ai" && message.id === null;

const updateStreamedAnswer = (messages: MessageProps[], update: (answer: AiMessageProps) => AiMessageProps) => {
  const last = messages[messages.length - 1];
  if (isStreamedAnswer(last)) {
    return [...messages.slice(0, -1), update(last)];
  }
  return [...messages, update({ type: "ai", text: "", id: null, steps: [] })];
};

export const appendToken = (messages: MessageProps[], token: string) =>
  updateStreamedAnswer(messages, (answer) => ({ ...answer, text: answer.text + token }));

export const moveTextToNarration = (messages: MessageProps[]) => {
  const last = messages[messages.length - 1];
  if (!isStreamedAnswer(last) || !last.text.trim()) {
    return messages;
  }
  const narration: AgentStep = { kind: "narration", text: last.text.trim() };
  return [...messages.slice(0, -1), { ...last, text: "", steps: [...(last.steps ?? []), narration] }];
};

export const startTool = (messages: MessageProps[], toolName: string) =>
  updateStreamedAnswer(messages, (answer) => ({
    ...answer,
    steps: [...(answer.steps ?? []), { kind: "tool", toolName, done: false }],
  }));

export const finishTool = (messages: MessageProps[]) => {
  const last = messages[messages.length - 1];
  if (!isStreamedAnswer(last) || !last.steps) {
    return messages;
  }
  const index = last.steps.map((step) => step.kind === "tool" && !step.done).lastIndexOf(true);
  if (index === -1) {
    return messages;
  }
  const steps = last.steps.map((step, i) => (i === index ? { ...step, done: true } : step));
  return [...messages.slice(0, -1), { ...last, steps }];
};
