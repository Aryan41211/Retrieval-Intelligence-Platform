import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred';
    toast.error(message);
    return Promise.reject(error);
  }
);

export type {
  Document,
  DocumentUploadRequest,
  DocumentUploadResponse,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  RetrievalResult,
  RetrievalRequest,
  RetrievalResponse,
  RetrievalInspectResponse,
  EvaluationResult,
  EvaluationRequest,
  EvaluationResponse,
  ExperimentResult,
  ExperimentRequest,
  ExperimentResponse,
  SettingsResponse,
  Theme,
} from './types';
