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
  } catch {}
}

export function clearChat(userId) {
  try {
    localStorage.removeItem(key(userId))
  } catch {}
}

export function countAnsweredQuestions(userId) {
  return loadChat(userId).filter((message) => message.role === 'assistant' && !message.error).length
}
