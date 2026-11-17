const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function requestJson(path, options) {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      // Use the status message when the server did not return JSON.
    }
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}
