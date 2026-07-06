import { useEffect, useState } from 'react';

export function useApiStream<T>(
  url: string,
  options?: { signal?: AbortSignal }
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    async function fetchStream() {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(url, { signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let result = '';
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const payload = line.slice(6);
              if (payload === '[DONE]') {
                setData(result as T);
                return;
              }
              try {
                const parsed = JSON.parse(payload);
                result = parsed;
                setData(parsed);
              } catch {
                result += payload;
                setData(result as T);
              }
            }
          }
        }

        setData(result as T);
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError(err instanceof Error ? err : new Error('Stream failed'));
        }
      } finally {
        setIsLoading(false);
      }
    }

    if (options?.signal) {
      options.signal.addEventListener('abort', () => controller.abort());
    }

    fetchStream();

    return () => controller.abort();
  }, [url, options?.signal]);

  return { data, isLoading, error };
}
