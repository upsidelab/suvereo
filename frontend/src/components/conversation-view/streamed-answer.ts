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

export const endStreamedMessage = (messages: MessageProps[]): MessageProps[] => {
  const last = messages[messages.length - 1];
  if (!isStreamedAnswer(last)) {
    return messages;
  }
  return [...messages.slice(0, -1), { ...last, type: "intermediate_step" }];
};

const isEndedStreamedMessage = (message: MessageProps | undefined): message is TextMessageProps =>
  !!message && message.type === "intermediate_step" && message.id === null;

export const markAsAnswer = (messages: MessageProps[], id: number, text: string): MessageProps[] => {
  const answer: TextMessageProps = { type: "ai", text, id };
  const last = messages[messages.length - 1];
  if (!isEndedStreamedMessage(last)) {
    return [...messages, answer];
  }
  return [...messages.slice(0, -1), answer];
};
