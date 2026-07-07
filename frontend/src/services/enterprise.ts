import { api } from './api';
import type {
  AdminStats,
  AuditLog,
  Conversation,
  ConversationDetail,
  Message,
  TokenResponse,
  User,
  UserProfileUpdate,
  Workspace,
  WorkspaceMember,
} from '@/types';

export const enterpriseApi = {
  // --- Authentication -------------------------------------------------------
  register: async (payload: {
    email: string;
    username: string;
    password: string;
  }): Promise<TokenResponse> => {
    const { data } = await api.post('/auth/register', payload);
    return data;
  },
  login: async (payload: { identifier: string; password: string }): Promise<TokenResponse> => {
    const { data } = await api.post('/auth/login', payload);
    return data;
  },
  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken });
    return data;
  },
  requestPasswordReset: async (email: string): Promise<void> => {
    await api.post('/auth/password-reset/request', { email });
  },
  confirmPasswordReset: async (token: string, newPassword: string): Promise<void> => {
    await api.post('/auth/password-reset/confirm', { token, new_password: newPassword });
  },
  verifyEmail: async (token: string): Promise<void> => {
    await api.post('/auth/email/verify', { token });
  },
  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },

  // --- Users ----------------------------------------------------------------
  me: async (): Promise<User> => {
    const { data } = await api.get('/users/me');
    return data;
  },
  updateProfile: async (payload: UserProfileUpdate): Promise<User> => {
    const { data } = await api.patch('/users/me', payload);
    return data;
  },
  listUsers: async (limit = 50, offset = 0): Promise<User[]> => {
    const { data } = await api.get('/users', { params: { limit, offset } });
    return data;
  },
  deactivateUser: async (userId: string): Promise<User> => {
    const { data } = await api.post(`/users/${userId}/deactivate`);
    return data;
  },

  // --- Workspaces -----------------------------------------------------------
  createWorkspace: async (payload: {
    name: string;
    description?: string;
    is_shared_kb?: boolean;
  }): Promise<Workspace> => {
    const { data } = await api.post('/workspaces', payload);
    return data;
  },
  myWorkspaces: async (): Promise<Workspace[]> => {
    const { data } = await api.get('/workspaces');
    return data;
  },
  sharedKnowledgeBases: async (): Promise<Workspace[]> => {
    const { data } = await api.get('/workspaces/shared');
    return data;
  },
  getWorkspace: async (workspaceId: string): Promise<Workspace> => {
    const { data } = await api.get(`/workspaces/${workspaceId}`);
    return data;
  },
  addMember: async (
    workspaceId: string,
    userId: string,
    role = 'member'
  ): Promise<WorkspaceMember> => {
    const { data } = await api.post(`/workspaces/${workspaceId}/members`, {
      user_id: userId,
      role,
    });
    return data;
  },
  removeMember: async (workspaceId: string, userId: string): Promise<void> => {
    await api.delete(`/workspaces/${workspaceId}/members/${userId}`);
  },
  listMembers: async (workspaceId: string): Promise<WorkspaceMember[]> => {
    const { data } = await api.get(`/workspaces/${workspaceId}/members`);
    return data;
  },

  // --- Conversations ---------------------------------------------------------
  createConversation: async (payload: {
    title?: string;
    workspace_id?: string;
  }): Promise<Conversation> => {
    const { data } = await api.post('/conversations', payload);
    return data;
  },
  listConversations: async (workspaceId?: string): Promise<Conversation[]> => {
    const { data } = await api.get('/conversations', {
      params: workspaceId ? { workspace_id: workspaceId } : {},
    });
    return data;
  },
  searchConversations: async (query: string): Promise<Conversation[]> => {
    const { data } = await api.get('/conversations/search', { params: { q: query } });
    return data;
  },
  getConversation: async (conversationId: string): Promise<ConversationDetail> => {
    const { data } = await api.get(`/conversations/${conversationId}`);
    return data;
  },
  addMessage: async (
    conversationId: string,
    payload: { role: string; content: string; citations?: Record<string, unknown> }
  ): Promise<Message> => {
    const { data } = await api.post(`/conversations/${conversationId}/messages`, payload);
    return data;
  },
  renameConversation: async (conversationId: string, title: string): Promise<Conversation> => {
    const { data } = await api.patch(`/conversations/${conversationId}`, { title });
    return data;
  },
  deleteConversation: async (conversationId: string): Promise<void> => {
    await api.delete(`/conversations/${conversationId}`);
  },
  exportConversation: async (conversationId: string, format: 'json' | 'markdown' | 'pdf') => {
    const { data } = await api.get(`/conversations/${conversationId}/export`, {
      params: { fmt: format },
      responseType: 'blob',
    });
    return data;
  },

  // --- Admin ----------------------------------------------------------------
  dashboard: async (): Promise<AdminStats> => {
    const { data } = await api.get('/admin/dashboard');
    return data;
  },
  auditLogs: async (limit = 50, offset = 0): Promise<AuditLog[]> => {
    const { data } = await api.get('/admin/audit', { params: { limit, offset } });
    return data;
  },
};
