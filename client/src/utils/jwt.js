// Reads the expiry from the access token issued by /auth/login. The signature is
// verified by the server; the client only uses `exp` to end the session on time.
export function getTokenExpiry(token) {
  if (!token) return null
  try {
    const payload = token.split('.')[1]
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    const { exp } = JSON.parse(json)
    return typeof exp === 'number' ? new Date(exp * 1000) : null
  } catch {
    return null
  }
}

export function isTokenExpired(token) {
  const expiry = getTokenExpiry(token)
  return !expiry || expiry.getTime() <= Date.now()
}
