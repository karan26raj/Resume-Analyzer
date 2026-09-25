import { useCallback, useEffect, useState } from 'react'

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
