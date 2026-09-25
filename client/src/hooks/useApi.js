import { useCallback, useEffect, useRef, useState } from 'react'

export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const hasData = useRef(false)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const run = useCallback((signal) => {
    if (hasData.current) setRefreshing(true)
    else setLoading(true)
    setError(null)

    return fetcherRef
      .current(signal)
      .then((result) => {
        if (signal?.aborted) return
        hasData.current = true
        setData(result)
      })
      .catch((err) => {
        if (err?.name === 'AbortError' || signal?.aborted) return
        setError(err)
      })
      .finally(() => {
        if (signal?.aborted) return
        setLoading(false)
        setRefreshing(false)
      })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    run(controller.signal)
    return () => controller.abort()
  }, deps)

  const reload = useCallback(() => run(), [run])

  return { data, setData, error, loading, refreshing, reload }
}
