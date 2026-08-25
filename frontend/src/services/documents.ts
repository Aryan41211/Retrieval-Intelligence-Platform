import { api } from './api';
import type { DocumentUploadResponse } from '@/types';

export interface DocumentSummary {
  document_id: string;
  filename: string;
  namespace: string;
  chunk_count: number;
  status: string;
}

export interface SupportedFormats {
  extensions: string[];
  max_file_size_mb: number;
}

export const documentsApi = {
  /** Report the document API status. */
  status: async () => {
    const { data } = await api.get('/documents');
    return data;
  },

  /**
   * List indexed documents across every knowledge base the caller can read.
   *
   * The previous implementation called `GET /documents`, which returns a status
   * string, so the list silently rendered empty forever.
   */
  list: async (): Promise<DocumentSummary[]> => {
    const { data } = await api.get('/documents/list');
    return data;
  },

  /** Remove a document's chunks from a knowledge base. */
  remove: async (documentId: string, workspaceId?: string): Promise<void> => {
    await api.delete(`/documents/${documentId}`, {
      params: workspaceId ? { workspace_id: workspaceId } : {},
    });
  },

  /** File types and size limit the upload endpoint accepts. */
  supportedFormats: async (): Promise<SupportedFormats> => {
    const { data } = await api.get('/documents/supported-formats');
    return data;
  },

  /**
   * Upload a file (PDF, DOCX, Markdown, plain text).
   *
   * Posts to the multipart endpoint. The previous implementation sent FormData
   * to `/documents/upload`, which accepts JSON only, so file upload never worked.
   *
   * @param file - The file to ingest.
   * @param workspaceId - Target workspace; omit for the caller's private KB.
   * @param onProgress - Receives 0-100 as the upload streams.
   */
  uploadFile: async (
    file: File,
    workspaceId?: string,
    onProgress?: (percent: number) => void
  ): Promise<DocumentUploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    if (workspaceId) form.append('workspace_id', workspaceId);

    const { data } = await api.post('/documents/upload/file', form, {
      // Let the browser set the multipart boundary; a hardcoded Content-Type
      // omits it and the server cannot parse the body.
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total));
        }
      },
    });
    return data;
  },

  /** Ingest a document supplied as plain text. */
  uploadText: async (
    filename: string,
    content: string,
    workspaceId?: string
  ): Promise<DocumentUploadResponse> => {
    const { data } = await api.post('/documents/upload', {
      filename,
      content,
      ...(workspaceId ? { workspace_id: workspaceId } : {}),
    });
    return data;
  },
};
