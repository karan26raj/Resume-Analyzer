import { useCallback, useEffect, useState } from 'react'

// Callback ref so the observer re-attaches when the measured element remounts
// (e.g. switching a chart from table view back to chart view).
export function useElementWidth() {
  const [element, setElement] = useState(null)
  const [width, setWidth] = useState(0)
  const ref = useCallback((node) => setElement(node), [])

  useEffect(() => {
    if (!element) return undefined
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    observer.observe(element)
    return () => observer.disconnect()
  }, [element])

  return [ref, width]
}
