"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { ChatMessage, ProjectId, ToolCallData, ToolResultData } from "@/lib/types";

export function useChat(projectId: ProjectId) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (content: string, contextNodeIds: string[] = []) => {
      if (!content.trim()) return;
      setSending(true);
      setError(null);
      const teacherMessage: ChatMessage = {
        id: `teacher_${Date.now()}`,
        projectId,
        role: "teacher",
        content,
        toolCall: null,
        evidence: [],
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, teacherMessage]);
      try {
        const result = await api.sendMessage(projectId, content, contextNodeIds);
        const toolMessages = buildToolMessages(projectId, result.toolCalls, result.toolResults ?? []);
        setMessages((prev) => [...prev, ...toolMessages, result.message]);
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Send failed");
        setMessages((prev) => [
          ...prev,
          {
            id: `error_${Date.now()}`,
            projectId,
            role: "system",
            content: err instanceof Error ? err.message : "发送失败",
            toolCall: null,
            evidence: [],
            createdAt: new Date().toISOString(),
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [projectId],
  );

  const askQuestion = useCallback(
    async (question: string) => {
      if (!question.trim()) return;
      setSending(true);
      setError(null);
      try {
        const result = await api.askQuestion(projectId, question);
        // Convert ask response to a chat message for display
        const msg: ChatMessage = {
          id: `ask_${Date.now()}`,
          projectId,
          role: "agent",
          content: result.answer,
          toolCall: null,
          evidence: result.citations as string[],
          createdAt: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, msg]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ask failed");
      } finally {
        setSending(false);
      }
    },
    [projectId],
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, sending, error, sendMessage, askQuestion, clearMessages };
}

function buildToolMessages(
  projectId: ProjectId,
  toolCalls: unknown[],
  toolResults: ToolResultData[],
): ChatMessage[] {
  return toolCalls
    .map((call, index) => normalizeToolCall(call, toolResults[index]))
    .filter((toolCall): toolCall is ToolCallData => toolCall !== null)
    .map((toolCall, index) => ({
      id: `tool_${Date.now()}_${index}`,
      projectId,
      role: "tool_call",
      content: `工具调用：${toolCall.name}`,
      toolCall,
      evidence: [],
      createdAt: new Date().toISOString(),
    }));
}

function normalizeToolCall(call: unknown, result?: ToolResultData): ToolCallData | null {
  if (!isRecord(call)) return null;
  const fn = isRecord(call.function) ? call.function : call;
  const name = typeof fn.name === "string" ? fn.name : result?.name;
  if (!name) return null;
  return {
    name,
    params: parseParams(fn.arguments ?? fn.params),
    result: result?.result ?? null,
  };
}

function parseParams(value: unknown): Record<string, unknown> {
  if (isRecord(value)) return value;
  if (typeof value !== "string") return {};
  try {
    const parsed: unknown = JSON.parse(value);
    return isRecord(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
