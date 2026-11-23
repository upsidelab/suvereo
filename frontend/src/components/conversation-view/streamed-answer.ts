import type { MessageProps, TextMessageProps } from "@/components/conversation-view/chat-session.tsx";

// The start of a reply is held back: if a tool call follows, that text was narration and is dropped unseen.
const HOLD_BACK_CHARS = 200;

const isStreamedAnswer = (message: MessageProps | undefined): message is TextMessageProps =>
  !!message && message.type === "ai" && message.id === null;

export const isHeldBack = (message: MessageProps) =>
  isStreamedAnswer(message) && message.text.length < HOLD_BACK_CHARS;

export const appendToken = (messages: MessageProps[], token: string): MessageProps[] => {
  const last = messages[messages.length - 1];
  if (isStreamedAnswer(last)) {
    return [...messages.slice(0, -1), { ...last, text: last.text + token }];
  }
  return [...messages, { type: "ai", text: token, id: null }];
};

export const dropNarration = (messages: MessageProps[]) =>
  isStreamedAnswer(messages[messages.length - 1]) ? messages.slice(0, -1) : messages;
