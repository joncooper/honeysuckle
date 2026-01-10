/**
 * API client utilities for Honeysuckle.
 */

const API_BASE = '/api'

/**
 * Fetch wrapper with error handling.
 */
async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API error: ${response.status}`)
  }

  return response.json()
}

/**
 * Health check.
 */
export async function checkHealth(): Promise<{ status: string }> {
  return apiFetch('/health')
}

/**
 * WebSocket connection helper.
 */
export function createAudioWebSocket(): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return new WebSocket(`${protocol}//${host}/ws/audio`)
}
