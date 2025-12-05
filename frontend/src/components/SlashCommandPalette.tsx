/**
 * Floating command palette for slash commands in the Proposal Copilot editor.
 */
import { useEffect, useRef } from 'react'
import {
  Pencil,
  Maximize2,
  History,
  FileText,
  Building,
  Zap,
  List,
  AlignLeft,
  Table,
  Heading,
  ClipboardList,
  Shield,
  Quote,
  Loader2,
  type LucideIcon,
} from 'lucide-react'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { SlashCommandDef } from '@/types/copilot'
import { cn } from '@/lib/utils'

const ICONS: Record<string, LucideIcon> = {
  Pencil,
  Maximize2,
  History,
  FileText,
  Building,
  Zap,
  List,
  AlignLeft,
  Table,
  Heading,
  ClipboardList,
  Shield,
  Quote,
}

const CATEGORY_LABELS: Record<string, string> = {
  generate: 'Generate',
  transform: 'Transform',
  format: 'Format',
  analyze: 'Analyze',
}

interface SlashCommandPaletteProps {
  isOpen: boolean
  position: { x: number; y: number } | null
  searchQuery: string
  onSearchChange: (query: string) => void
  groupedCommands: Record<string, SlashCommandDef[]>
  onSelect: (command: SlashCommandDef) => void
  isExecuting: boolean
  hasSelection: boolean
}

export function SlashCommandPalette({
  isOpen,
  position,
  searchQuery,
  onSearchChange,
  groupedCommands,
  onSelect,
  isExecuting,
  hasSelection,
}: SlashCommandPaletteProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      // Small delay to ensure the element is visible
      requestAnimationFrame(() => {
        inputRef.current?.focus()
      })
    }
  }, [isOpen])

  if (!isOpen || !position) return null

  const categoryOrder = ['generate', 'transform', 'format', 'analyze']

  // Clamp position to viewport
  const clampedPosition = {
    x: Math.max(10, Math.min(position.x, window.innerWidth - 300)),
    y: Math.max(10, Math.min(position.y, window.innerHeight - 400)),
  }

  return (
    <div
      data-slash-command-palette
      className="fixed z-50 w-72 rounded-lg border bg-popover shadow-lg animate-in fade-in-0 zoom-in-95"
      style={{
        left: `${clampedPosition.x}px`,
        top: `${clampedPosition.y}px`,
      }}
    >
      <Command className="rounded-lg" shouldFilter={false}>
        <CommandInput
          ref={inputRef}
          placeholder="Search commands..."
          value={searchQuery}
          onValueChange={onSearchChange}
          className="border-0"
        />
        <CommandList className="max-h-[300px]">
          <CommandEmpty>No commands found.</CommandEmpty>

          {categoryOrder.map((category) => {
            const commands = groupedCommands[category]
            if (!commands || commands.length === 0) return null

            return (
              <CommandGroup key={category} heading={CATEGORY_LABELS[category]}>
                {commands.map((cmd) => {
                  const Icon = ICONS[cmd.icon] || Pencil
                  const isDisabled = cmd.requiresSelection && !hasSelection

                  return (
                    <CommandItem
                      key={cmd.id}
                      value={cmd.name}
                      onSelect={() => {
                        if (!isDisabled && !isExecuting) {
                          onSelect(cmd)
                        }
                      }}
                      disabled={isDisabled || isExecuting}
                      className={cn(
                        'flex items-center gap-3 py-2 cursor-pointer',
                        isDisabled && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-md border bg-background">
                        {isExecuting ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Icon className="h-4 w-4" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium">{cmd.name}</div>
                        <div className="text-xs text-muted-foreground truncate">
                          {isDisabled ? 'Select text first' : cmd.description}
                        </div>
                      </div>
                      {cmd.shortcut && (
                        <span className="text-xs text-muted-foreground">
                          {cmd.shortcut}
                        </span>
                      )}
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            )
          })}
        </CommandList>
      </Command>

      <div className="border-t px-3 py-2 text-xs text-muted-foreground">
        Type to filter • ↑↓ navigate • Enter select • Esc close
      </div>
    </div>
  )
}
