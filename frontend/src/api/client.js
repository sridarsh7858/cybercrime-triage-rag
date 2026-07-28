import { API_BASE_URL } from "../lib/config";

/**
 * Submit an incident to the backend RAG pipeline.
 * Mirrors POST /api/v1/analyze which accepts a multipart form with an optional
 * `query` text field and an optional `file` image, and returns
 * { query, analysis, retrieved_context_count }.
 *
 * @param {{ query?: string, file?: File | null }} payload
 * @returns {Promise<{query: string, analysis: string, retrieved_context_count: number}>}
 */
export async function analyzeIncident({ query, file }) {
  const form = new FormData();
  if (query && query.trim()) form.append("query", query.trim());
  if (file) form.append("file", file);

  let res;
  try {
    res = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
      method: "POST",
      body: form,
    });
  } catch {
    throw new Error(
      `Could not reach the backend at ${API_BASE_URL}. Is the FastAPI server running?`
    );
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    // Non-JSON error body (e.g. proxy/HTML error page)
  }

  if (!res.ok) {
    const detail =
      (data && (data.detail || data.message)) ||
      `Request failed with status ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}
