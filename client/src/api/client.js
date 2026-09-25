export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

const TOKEN_KEY = 'resumeiq.token'

let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
  }
}

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

function messageFromBody(body, status) {
  const message = detailMessage(body, status)
  return status >= 500 && body?.request_id ? `${message} (ref ${body.request_id.slice(0, 8)})` : message
}

function detailMessage(body, status) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : ''
        return field ? `${field}: ${item.msg}` : item.msg
      })
      .join('; ')
  }
  if (status === 0) return 'Cannot reach the server. Is the API running?'
  if (status >= 500) return 'The server ran into a problem. Please try again.'
  return `Request failed (${status})`
}

function handleUnauthorized(status, path) {
  if (status === 401 && !path.startsWith('/auth/login') && unauthorizedHandler) {
    unauthorizedHandler()
  }
}

export async function apiRequest(path, { method = 'GET', body, query, signal, auth = true } = {}) {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin)
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
    })
  }

  const headers = { Accept: 'application/json' }
  const token = auth ? getToken() : null
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError(messageFromBody(null, 0), 0)
  }

  if (response.status === 204) return null

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    handleUnauthorized(response.status, path)
    throw new ApiError(messageFromBody(data, response.status), response.status, data)
  }

  return data
}

export function uploadFile(path, file, { onProgress, fieldName = 'file' } = {}) {
  let xhr
  const promise = new Promise((resolve, reject) => {
    xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE_URL}${path}`)
    xhr.setRequestHeader('Accept', 'application/json')
    const token = getToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total)
    }

    xhr.onload = () => {
      let data = null
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null
      } catch {
        data = null
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data)
      } else {
        handleUnauthorized(xhr.status, path)
        reject(new ApiError(messageFromBody(data, xhr.status), xhr.status, data))
      }
    }
    xhr.onerror = () => reject(new ApiError(messageFromBody(null, 0), 0))
    xhr.onabort = () => reject(new DOMException('Upload cancelled', 'AbortError'))

    const form = new FormData()
    form.append(fieldName, file)
    xhr.send(form)
  })

  return { promise, abort: () => xhr?.abort() }
}
