import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from './errors'

interface LoaderState<T> {
  key: string | null
  data?: T
  error?: string
}

/**
 * Load data for `key` with a stable, module-level `load` function. Loading state is derived from
 * whether the stored result belongs to the current key, so switching keys never shows stale data.
 */
export function useLoader<T>(key: string, load: (key: string) => Promise<T>) {
  const [state, setState] = useState<LoaderState<T>>({ key: null })

  useEffect(() => {
    let active = true
    load(key).then(
      (data) => {
        if (active) setState({ key, data })
      },
      (error: unknown) => {
        if (active) setState({ key, error: errorMessage(error) })
      },
    )
    return () => {
      active = false
    }
  }, [key, load])

  const setData = useCallback((data: T) => setState({ key, data }), [key])
  const current = state.key === key ? state : { key, data: undefined, error: undefined }

  return {
    data: current.data,
    error: current.error,
    loading: current.data === undefined && current.error === undefined,
    setData,
  }
}
