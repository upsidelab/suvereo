import type { MessageProps, TextMessageProps } from "@/components/conversation-view/chat-session.tsx";

const isStreamedAnswer = (message: MessageProps | undefined): message is TextMessageProps =>
  !!message && message.type === "ai" && message.id === null;

export const appendToken = (messages: MessageProps[], token: string): MessageProps[] => {
  const last = messages[messages.length - 1];
  if (isStreamedAnswer(last)) {
    return [...messages.slice(0, -1), { ...last, text: last.text + token }];
  }
  return [...messages, { type: "ai", text: token, id: null }];
};

export const endToolCallNarration = (messages: MessageProps[]): MessageProps[] => {
  const last = messages[messages.length - 1];
  if (!isStreamedAnswer(last)) {
    return messages;
  }
  return [...messages.slice(0, -1), { ...last, type: "intermediate_step" }];
};
