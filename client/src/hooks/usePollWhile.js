import { useEffect, useRef } from 'react'

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
