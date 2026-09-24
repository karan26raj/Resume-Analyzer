import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Runs an API call and tracks its loading / error / data state.
 * `reload()` refetches while keeping the previous data visible (no skeleton flash).
 */
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const reload = useCallback(() => run(), [run])

  return { data, setData, error, loading, refreshing, reload }
}
