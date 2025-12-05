/**
 * Hook for slash command detection and execution in the Proposal Copilot editor.
 */
import { useState, useCallback, useRef, useEffect, type RefObject } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/services/api'
import {
  SLASH_COMMANDS,
  SlashCommandDef,
  SlashCommandId,
  TextSelection,
  CommandExecutionResult,
} from '@/types/copilot'

interface UseSlashCommandsOptions {
  rfpId: string
  sectionId: string
  content: string
  onContentChange: (content: string) => void
}

interface UseSlashCommandsReturn {
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  position: { x: number; y: number } | null
  searchQuery: string
  setSearchQuery: (query: string) => void
  filteredCommands: SlashCommandDef[]
  groupedCommands: Record<string, SlashCommandDef[]>
  selection: TextSelection | null
  slashStartIndex: number | null
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  handleInput: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  executeCommand: (command: SlashCommandDef) => Promise<CommandExecutionResult | null>
  isExecuting: boolean
  textareaRef: RefObject<HTMLTextAreaElement>
}

export function useSlashCommands({
  rfpId,
  sectionId,
  content,
  onContentChange,
}: UseSlashCommandsOptions): UseSlashCommandsReturn {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null)
  const [selection, setSelection] = useState<TextSelection | null>(null)
  const [slashStartIndex, setSlashStartIndex] = useState<number | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Filter commands based on search and selection state
  const filteredCommands = SLASH_COMMANDS.filter((cmd) => {
    const matchesSearch =
      cmd.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cmd.description.toLowerCase().includes(searchQuery.toLowerCase())

    // If requires selection but none exists, still show but will be disabled
    return matchesSearch
  })

  // Group commands by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = []
    acc[cmd.category].push(cmd)
    return acc
  }, {} as Record<string, SlashCommandDef[]>)

  // Detect "/" keystroke
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === '/' && !isOpen) {
      const textarea = e.currentTarget
      const cursorPos = textarea.selectionStart

      // Check if "/" is at start of line or after whitespace
      const beforeCursor = content.slice(0, cursorPos)
      const lastChar = beforeCursor.slice(-1)

      if (cursorPos === 0 || /\s/.test(lastChar)) {
        // Get cursor position for dropdown placement
        const rect = textarea.getBoundingClientRect()
        const lineHeight = parseInt(getComputedStyle(textarea).lineHeight) || 20
        const lines = beforeCursor.split('\n')
        const currentLine = lines.length

        // Calculate position - place below current line
        setPosition({
          x: rect.left + 10,
          y: rect.top + Math.min(currentLine * lineHeight, rect.height - 300) + 20,
        })

        setSlashStartIndex(cursorPos)
        setIsOpen(true)
        setSearchQuery('')

        // Capture current selection (text selected before typing "/")
        const selStart = textarea.selectionStart
        const selEnd = textarea.selectionEnd
        if (selStart !== selEnd) {
          setSelection({
            start: selStart,
            end: selEnd,
            text: content.slice(selStart, selEnd),
          })
        } else {
          setSelection(null)
        }
      }
    }

    // Handle escape to close
    if (e.key === 'Escape' && isOpen) {
      setIsOpen(false)
      setSearchQuery('')
    }
  }, [content, isOpen])

  // Update search query as user types after "/"
  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (isOpen && slashStartIndex !== null) {
      const newContent = e.target.value
      const cursorPos = e.target.selectionStart

      // Extract text after the slash
      const textAfterSlash = newContent.slice(slashStartIndex + 1, cursorPos)

      // If user typed space or newline, close the palette
      if (/[\s\n]/.test(textAfterSlash.slice(-1))) {
        setIsOpen(false)
        setSearchQuery('')
        return
      }

      setSearchQuery(textAfterSlash)
    }
  }, [isOpen, slashStartIndex])

  // Execute command mutation (non-streaming)
  const executeMutation = useMutation({
    mutationFn: async ({
      command,
      selectedText,
      context,
    }: {
      command: SlashCommandId
      selectedText: string
      context: string
    }) => {
      return api.copilot.executeCommand(rfpId, {
        command,
        selected_text: selectedText,
        context,
        section_id: sectionId,
      })
    },
    onSuccess: (data) => {
      // Replace selected text or insert at cursor
      if (selection && selection.text) {
        // Replace selection with result
        const before = content.slice(0, selection.start)
        const after = content.slice(selection.end)
        onContentChange(before + data.result + after)
      } else if (slashStartIndex !== null) {
        // Remove the slash command text and insert result
        const before = content.slice(0, slashStartIndex)
        const cursorPos = textareaRef.current?.selectionStart || slashStartIndex
        const after = content.slice(cursorPos)
        onContentChange(before + data.result + after)
      }

      setIsOpen(false)
      setSearchQuery('')
      setSlashStartIndex(null)
      setSelection(null)
    },
  })

  // Execute command handler
  const executeCommand = useCallback(async (command: SlashCommandDef): Promise<CommandExecutionResult | null> => {
    if (command.isStreaming) {
      // For streaming commands, return the command info
      // Parent component will handle streaming
      setIsOpen(false)
      return {
        command,
        selectedText: selection?.text || '',
        context: content,
        slashStartIndex,
      }
    }

    // Non-streaming command - execute directly
    await executeMutation.mutateAsync({
      command: command.id,
      selectedText: selection?.text || '',
      context: content,
    })

    return null
  }, [selection, content, slashStartIndex, executeMutation])

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (isOpen && !(e.target as Element)?.closest('[data-slash-command-palette]')) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  return {
    isOpen,
    setIsOpen,
    position,
    searchQuery,
    setSearchQuery,
    filteredCommands,
    groupedCommands,
    selection,
    slashStartIndex,
    handleKeyDown,
    handleInput,
    executeCommand,
    isExecuting: executeMutation.isPending,
    textareaRef,
  }
}
