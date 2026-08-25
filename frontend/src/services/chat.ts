import { api } from './api';
import { enterpriseApi } from './enterprise';
import { tokenStore } from './tokenStore';
import type { ChatMessage, ChatRequest, ChatResponse } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Error payload the backend emits on the SSE channel when generation fails.
 * It carries a correlation id rather than raw exception text.
 */
interface ChatStreamError {
  error: string;
  correlation_id?: string;
  conversation_id?: string;
}

function isStreamError(value: unknown): value is ChatStreamError {
  return typeof value === 'object' && value !== null && 'error' in value;
}

/** Citation shape used across the chat and citation pages. */
export type Citation = NonNullable<ChatResponse['citations']>[number];

/** A rendered chat turn, including any citations attached to an answer. */
export interface ChatTurn extends ChatMessage {
  id: string;
  citations?: Citation[];
}

/** Roles the UI knows how to render. */
const KNOWN_ROLES: ReadonlyArray<ChatMessage['role']> = ['user', 'assistant', 'system'];

function toRole(value: string): ChatMessage['role'] {
  return (KNOWN_ROLES as readonly string[]).includes(value)
    ? (value as ChatMessage['role'])
    : 'assistant';
}

/**
 * Recover the citation array from a persisted message.
 *
 * Messages store citations as a JSON object, so the array is nested under
 * `items` when it was written by this client.
 */
function toCitations(stored: Record<string, unknown> | null | undefined): Citation[] | undefined {
  if (!stored) return undefined;
  const items = (stored as { items?: unknown }).items;
  return Array.isArray(items) ? (items as Citation[]) : undefined;
}

/**
 * Stream a grounded answer from `POST /chat`.
 *
 * The endpoint responds with `text/event-stream`, so it is read with fetch and
 * parsed as SSE. The previous implementation posted with axios and treated the
 * body as JSON, which never parsed.
 */
async function streamAnswer(
  payload: ChatRequest,
  signal?: AbortSignal,
  onEvent?: (chunk: ChatResponse) => void
): Promise<ChatResponse> {
  const token = tokenStore.getAccessToken();
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      detail = body?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let last: ChatResponse | null = null;

  // SSE frames are newline-delimited and can be split across reads, so the
  // trailing partial line is carried into the next iteration.
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw || raw === '[DONE]') continue;

      let parsed: unknown;
      try {
        parsed = JSON.parse(raw);
      } catch {
        continue;
      }

      if (isStreamError(parsed)) {
        const suffix = parsed.correlation_id ? ` (ref: ${parsed.correlation_id})` : '';
        throw new Error(`${parsed.error}${suffix}`);
      }

      last = parsed as ChatResponse;
      onEvent?.(last);
    }
  }

  if (!last) throw new Error('The server returned an empty response.');
  return last;
}

export const chatApi = {
  status: async () => {
    const { data } = await api.get('/chat');
    return data;
  },

  /**
   * Load the persisted turns of a conversation.
   *
   * Backed by the conversations API. The previous implementation called
   * `GET /chat`, which returns a status string, so history was always empty.
   *
   * @param conversationId - Conversation to load; empty when none started yet.
   */
  history: async (conversationId?: string): Promise<ChatTurn[]> => {
    if (!conversationId) return [];
    const conversation = await enterpriseApi.getConversation(conversationId);
    return (conversation.messages ?? []).map((message) => ({
      id: message.id,
      role: toRole(message.role),
      content: message.content,
      timestamp: message.created_at,
      citations: toCitations(message.citations),
    }));
  },

  /**
   * Send a message and persist both sides of the turn.
   *
   * Creates the conversation on first use so refreshing the page keeps history.
   *
   * @returns The generated response and the conversation it was stored in.
   */
  send: async (
    payload: ChatRequest,
    signal?: AbortSignal,
    onEvent?: (chunk: ChatResponse) => void
  ): Promise<ChatResponse & { conversation_id: string }> => {
    let conversationId = payload.conversation_id;
    if (!conversationId) {
      const created = await enterpriseApi.createConversation({
        title: payload.query.slice(0, 80),
      });
      conversationId = created.id;
    }

    await enterpriseApi.addMessage(conversationId, {
      role: 'user',
      content: payload.query,
    });

    const answer = await streamAnswer(
      { ...payload, conversation_id: conversationId },
      signal,
      onEvent
    );

    // Persist the answer. A storage failure must not discard a generated
    // answer the user is already looking at, so it is not propagated.
    try {
      await enterpriseApi.addMessage(conversationId, {
        role: 'assistant',
        content: answer.message.content,
        citations: answer.citations
          ? ({ items: answer.citations } as Record<string, unknown>)
          : undefined,
      });
    } catch {
      /* answer is still returned to the caller */
    }

    return { ...answer, conversation_id: conversationId };
  },

  /** Delete a conversation and all of its messages. */
  clear: async (conversationId: string): Promise<void> => {
    if (!conversationId) return;
    await enterpriseApi.deleteConversation(conversationId);
  },

  /** List the current user's conversations, most recently updated first. */
  list: async (limit = 50) => enterpriseApi.listConversations(undefined, limit),
};
