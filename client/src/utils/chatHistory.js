// The API has no conversation-history endpoint, so assistant answers (exactly as returned
// by /assistant/ask) are kept in this browser's storage, per user.
const MAX_MESSAGES = 200

function key(userId) {
  return `resumeiq.chat.${userId}`
}

export function loadChat(userId) {
  if (!userId) return []
  try {
    const raw = localStorage.getItem(key(userId))
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveChat(userId, messages) {
  if (!userId) return
  try {
    localStorage.setItem(key(userId), JSON.stringify(messages.slice(-MAX_MESSAGES)))
  } catch {
    // Storage full or unavailable: the conversation still works for this session.
  }
}

export function clearChat(userId) {
  try {
    localStorage.removeItem(key(userId))
  } catch {
    // ignore
  }
}

export function countAnsweredQuestions(userId) {
  return loadChat(userId).filter((message) => message.role === 'assistant' && !message.error).length
}
