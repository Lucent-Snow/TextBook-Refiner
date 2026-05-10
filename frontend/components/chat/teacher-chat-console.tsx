"use client";

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Bot, ChevronUp, Loader2, Send, Sparkles, Trash2, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@/hooks/use-chat";
import type { ChatMessage } from "@/lib/types";

interface TeacherChatConsoleProps {
  projectId: string;
}

export function TeacherChatConsole({ projectId }: TeacherChatConsoleProps) {
  const { messages, sending, sendMessage, clearMessages } = useChat(projectId);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const content = input.trim();
    setInput("");
    await sendMessage(content);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-11 items-center justify-between border-b border-slate-200 px-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-900">师生对话控制台</h3>
          <Badge variant="outline" className="rounded border-blue-200 bg-blue-50 text-[10px] text-blue-700">
            Agent
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <button className="text-xs text-slate-500 hover:text-slate-800" onClick={clearMessages}>
            清空记录
          </button>
          <Button variant="ghost" size="icon" className="h-7 w-7 text-slate-500" onClick={clearMessages}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
          <ChevronUp className="h-4 w-4 text-slate-400" />
        </div>
      </div>

      <ScrollArea className="min-h-0 flex-1 p-3" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="flex h-full min-h-36 flex-col items-center justify-center px-4 text-center text-xs text-slate-400">
            <Bot className="mb-2 h-7 w-7 text-slate-300" />
            <p className="font-medium text-slate-500">询问整合理由，或要求重建某本教材章节。</p>
            <p className="mt-1">例如：这个节点不要合并，按第 3 章重新构建。</p>
          </div>
        )}

        <div className="space-y-3">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>
      </ScrollArea>

      <div className="border-t border-slate-200 p-2">
        <div className="flex gap-2">
          <Textarea
            placeholder="输入问题或指令，Agent 会解析并执行图谱工具..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            className="min-h-9 max-h-20 resize-none rounded-md border-slate-200 text-sm"
          />
          <Button size="icon" className="h-9 w-9 shrink-0 bg-blue-600 hover:bg-blue-700" onClick={handleSend} disabled={sending || !input.trim()}>
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "system") {
    return (
      <div className="text-center">
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">{message.content}</span>
      </div>
    );
  }

  if (message.role === "tool_call") {
    return <ToolCallBubble message={message} />;
  }

  const isTeacher = message.role === "teacher";

  return (
    <div className={`flex gap-2 ${isTeacher ? "justify-end" : "justify-start"}`}>
      {!isTeacher && <Avatar tone="agent" />}
      <div
        className={`max-w-[82%] rounded-md px-3 py-2 text-xs leading-5 ${
          isTeacher
            ? "bg-blue-600 text-white"
            : "border border-slate-100 bg-slate-50 text-slate-700"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.evidence.length > 0 && (
          <div className="mt-1 text-[10px] opacity-75">引用 {message.evidence.length} 处教材证据</div>
        )}
      </div>
      {isTeacher && <Avatar tone="teacher" />}
    </div>
  );
}

function ToolCallBubble({ message }: { message: ChatMessage }) {
  if (!message.toolCall) return null;
  const hasError = Boolean(message.toolCall.result?.error);

  return (
    <div className="ml-8 rounded-md border border-blue-100 bg-blue-50/70 p-2 text-xs text-slate-700">
      <div className="mb-1 flex items-center gap-2">
        <Sparkles className="h-3.5 w-3.5 text-blue-600" />
        <span className="font-semibold text-blue-700">工具调用：{message.toolCall.name}</span>
        <Badge variant="outline" className={`ml-auto rounded text-[10px] ${hasError ? "border-red-200 text-red-600" : "border-emerald-200 text-emerald-700"}`}>
          {hasError ? "失败" : "已执行"}
        </Badge>
      </div>
      <pre className="max-h-20 overflow-auto whitespace-pre-wrap rounded border border-blue-100 bg-white p-2 text-[10px] leading-4 text-slate-600">
        {JSON.stringify({ params: message.toolCall.params, result: message.toolCall.result }, null, 2)}
      </pre>
    </div>
  );
}

function Avatar({ tone }: { tone: "teacher" | "agent" }) {
  const isAgent = tone === "agent";
  return (
    <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${isAgent ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"}`}>
      {isAgent ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
    </div>
  );
}
