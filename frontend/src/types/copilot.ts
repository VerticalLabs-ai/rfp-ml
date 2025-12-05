/**
 * Types for Proposal Copilot slash commands.
 */

export type SlashCommandId =
  | 'write'
  | 'expand'
  | 'summarize'
  | 'bullets'
  | 'paragraph'
  | 'formal'
  | 'simplify'
  | 'requirements'
  | 'compliance'
  | 'similar'
  | 'cite'
  | 'table'
  | 'heading'

export interface SlashCommandDef {
  id: SlashCommandId
  name: string
  description: string
  icon: string  // Lucide icon name
  category: 'generate' | 'transform' | 'format' | 'analyze'
  requiresSelection: boolean
  isStreaming: boolean
  shortcut?: string  // Keyboard shortcut hint
}

export const SLASH_COMMANDS: SlashCommandDef[] = [
  // Generate category
  {
    id: 'write',
    name: 'Write',
    description: 'Generate new content for this section',
    icon: 'Pencil',
    category: 'generate',
    requiresSelection: false,
    isStreaming: true,
  },
  {
    id: 'expand',
    name: 'Expand',
    description: 'Add more detail to selected text',
    icon: 'Maximize2',
    category: 'generate',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'similar',
    name: 'Similar Experience',
    description: 'Suggest relevant past performance',
    icon: 'History',
    category: 'generate',
    requiresSelection: false,
    isStreaming: true,
  },

  // Transform category
  {
    id: 'summarize',
    name: 'Summarize',
    description: 'Create a concise summary',
    icon: 'FileText',
    category: 'transform',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'formal',
    name: 'Make Formal',
    description: 'Use professional government tone',
    icon: 'Building',
    category: 'transform',
    requiresSelection: true,
    isStreaming: false,
  },
  {
    id: 'simplify',
    name: 'Simplify',
    description: 'Make text clearer and simpler',
    icon: 'Zap',
    category: 'transform',
    requiresSelection: true,
    isStreaming: false,
  },

  // Format category
  {
    id: 'bullets',
    name: 'To Bullets',
    description: 'Convert to bullet points',
    icon: 'List',
    category: 'format',
    requiresSelection: true,
    isStreaming: false,
  },
  {
    id: 'paragraph',
    name: 'To Paragraph',
    description: 'Convert bullets to paragraph',
    icon: 'AlignLeft',
    category: 'format',
    requiresSelection: true,
    isStreaming: false,
  },
  {
    id: 'table',
    name: 'To Table',
    description: 'Format as markdown table',
    icon: 'Table',
    category: 'format',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'heading',
    name: 'Add Heading',
    description: 'Generate section heading',
    icon: 'Heading',
    category: 'format',
    requiresSelection: false,
    isStreaming: false,
  },

  // Analyze category
  {
    id: 'requirements',
    name: 'Extract Requirements',
    description: 'List key requirements from text',
    icon: 'ClipboardList',
    category: 'analyze',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'compliance',
    name: 'Add Compliance',
    description: 'Add compliance language',
    icon: 'Shield',
    category: 'analyze',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'cite',
    name: 'Add Citations',
    description: 'Format with citations',
    icon: 'Quote',
    category: 'analyze',
    requiresSelection: true,
    isStreaming: true,
  },
]

export interface TextSelection {
  start: number
  end: number
  text: string
}

export interface CommandExecutionResult {
  command: SlashCommandDef
  selectedText: string
  context: string
  slashStartIndex: number | null
}

export interface CommandResponse {
  result: string
  command: string
  tokens_used: number
}
