import { useEffect, useRef } from 'react'

/**
 * Calls `refresh` every `intervalMs` while `active` is true, e.g. until background indexing finishes.
 * Pauses while the tab is hidden so an idle tab doesn't keep polling the API.
 */
export function usePollWhile(active, refresh, intervalMs = 3000) {
  const refreshRef = useRef(refresh)
  refreshRef.current = refresh

  useEffect(() => {
    if (!active) return undefined
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') refreshRef.current()
    }, intervalMs)
    return () => clearInterval(timer)
  }, [active, intervalMs])
}
