/**
 * Hook for RFP search functionality with debouncing and URL persistence.
 *
 * Features:
 * - Debounced search (300ms default)
 * - URL query parameter sync for shareable links
 * - Keyboard shortcut (Cmd/Ctrl+K) to focus search
 * - Search term highlighting utility
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

interface UseRfpSearchOptions {
  debounceMs?: number
  urlParamName?: string
  inputRef?: React.RefObject<HTMLInputElement>
}

interface UseRfpSearchResult {
  searchTerm: string
  debouncedSearchTerm: string
  setSearchTerm: (term: string) => void
  clearSearch: () => void
  inputRef: React.RefObject<HTMLInputElement>
  isSearching: boolean
}

/**
 * Custom hook for RFP search with debouncing and URL sync.
 */
export function useRfpSearch(options: UseRfpSearchOptions = {}): UseRfpSearchResult {
  const {
    debounceMs = 300,
    urlParamName = 'q',
  } = options

  const [searchParams, setSearchParams] = useSearchParams()
  const inputRef = useRef<HTMLInputElement>(null)

  // Initialize from URL param
  const initialSearch = searchParams.get(urlParamName) || ''
  const [searchTerm, setSearchTermState] = useState(initialSearch)
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState(initialSearch)
  const [isSearching, setIsSearching] = useState(false)

  // Debounce the search term
  useEffect(() => {
    if (searchTerm !== debouncedSearchTerm) {
      setIsSearching(true)
    }

    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm)
      setIsSearching(false)
    }, debounceMs)

    return () => clearTimeout(timer)
  }, [searchTerm, debounceMs, debouncedSearchTerm])

  // Sync debounced search term to URL
  useEffect(() => {
    const currentParam = searchParams.get(urlParamName) || ''

    if (debouncedSearchTerm !== currentParam) {
      const newParams = new URLSearchParams(searchParams)

      if (debouncedSearchTerm) {
        newParams.set(urlParamName, debouncedSearchTerm)
      } else {
        newParams.delete(urlParamName)
      }

      setSearchParams(newParams, { replace: true })
    }
  }, [debouncedSearchTerm, searchParams, setSearchParams, urlParamName])

  // Handle keyboard shortcut (Cmd/Ctrl+K)
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Cmd+K (Mac) or Ctrl+K (Windows/Linux)
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault()
        inputRef.current?.focus()
        inputRef.current?.select()
      }

      // Escape to blur and clear
      if (event.key === 'Escape' && document.activeElement === inputRef.current) {
        inputRef.current?.blur()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const setSearchTerm = useCallback((term: string) => {
    setSearchTermState(term)
  }, [])

  const clearSearch = useCallback(() => {
    setSearchTermState('')
    setDebouncedSearchTerm('')
    inputRef.current?.focus()
  }, [])

  return {
    searchTerm,
    debouncedSearchTerm,
    setSearchTerm,
    clearSearch,
    inputRef,
    isSearching,
  }
}

/**
 * Highlight matching terms in text.
 *
 * @param text - The text to search in
 * @param searchTerm - The term to highlight
 * @returns Array of text segments with highlight flags
 */
export function highlightMatches(
  text: string,
  searchTerm: string
): Array<{ text: string; highlight: boolean }> {
  if (!searchTerm || !text) {
    return [{ text: text || '', highlight: false }]
  }

  const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi')
  const parts = text.split(regex)

  return parts
    .filter(part => part.length > 0)
    .map(part => ({
      text: part,
      highlight: part.toLowerCase() === searchTerm.toLowerCase(),
    }))
}

/**
 * Escape special regex characters in a string.
 */
function escapeRegex(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Check if a string contains the search term (case-insensitive).
 */
export function matchesSearch(text: string | null | undefined, searchTerm: string): boolean {
  if (!text || !searchTerm) return false
  return text.toLowerCase().includes(searchTerm.toLowerCase())
}

/**
 * Component to render highlighted text.
 */
export function HighlightedText({
  text,
  searchTerm,
  className = '',
  highlightClassName = 'bg-yellow-200 dark:bg-yellow-800 rounded px-0.5',
}: {
  text: string
  searchTerm: string
  className?: string
  highlightClassName?: string
}) {
  const segments = highlightMatches(text, searchTerm)

  return (
    <span className={className}>
      {segments.map((segment, index) =>
        segment.highlight ? (
          <mark key={index} className={highlightClassName}>
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        )
      )}
    </span>
  )
}
