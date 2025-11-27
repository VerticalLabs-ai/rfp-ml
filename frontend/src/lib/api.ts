/**
 * API client for the RFP Bid Generation System
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

class ApiError extends Error {
  status: number
  data: unknown

  constructor(message: string, status: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const config: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  }

  const response = await fetch(url, config)

  if (!response.ok) {
    let errorData
    try {
      errorData = await response.json()
    } catch {
      errorData = { detail: response.statusText }
    }
    throw new ApiError(
      errorData.detail || `HTTP error ${response.status}`,
      response.status,
      errorData
    )
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),

  post: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  put: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  patch: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),

  // File upload helper
  upload: async <T>(endpoint: string, file: File, fieldName = 'file'): Promise<T> => {
    const formData = new FormData()
    formData.append(fieldName, file)

    const url = `${API_BASE_URL}${endpoint}`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }))
      throw new ApiError(
        errorData.detail || `HTTP error ${response.status}`,
        response.status,
        errorData
      )
    }

    return response.json()
  },

  // Download helper
  download: async (endpoint: string, filename: string): Promise<void> => {
    const url = `${API_BASE_URL}${endpoint}`
    const response = await fetch(url)

    if (!response.ok) {
      throw new ApiError(`Download failed: ${response.statusText}`, response.status)
    }

    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(downloadUrl)
  },
}

export { ApiError }
