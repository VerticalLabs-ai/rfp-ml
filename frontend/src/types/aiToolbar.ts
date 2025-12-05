export type AIActionId =
  | 'improve'
  | 'expand'
  | 'simplify'
  | 'formalize'
  | 'grammar'
  | 'readability'
  | 'passive'
  | 'jargon'

export interface AIAction {
  id: AIActionId
  name: string
  description: string
  icon: string
  category: 'transform' | 'analyze'
  requiresSelection: boolean
  isStreaming: boolean
}

export const AI_ACTIONS: AIAction[] = [
  {
    id: 'improve',
    name: 'Improve',
    description: 'Enhance clarity and impact',
    icon: 'Sparkles',
    category: 'transform',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'expand',
    name: 'Expand',
    description: 'Add more detail and depth',
    icon: 'Maximize2',
    category: 'transform',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'simplify',
    name: 'Simplify',
    description: 'Make easier to understand',
    icon: 'Minimize2',
    category: 'transform',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'formalize',
    name: 'Formalize',
    description: 'Professional government tone',
    icon: 'Briefcase',
    category: 'transform',
    requiresSelection: true,
    isStreaming: true,
  },
  {
    id: 'grammar',
    name: 'Grammar Check',
    description: 'Fix spelling and grammar',
    icon: 'SpellCheck',
    category: 'analyze',
    requiresSelection: false,
    isStreaming: false,
  },
  {
    id: 'readability',
    name: 'Readability',
    description: 'Score and suggestions',
    icon: 'Eye',
    category: 'analyze',
    requiresSelection: false,
    isStreaming: false,
  },
  {
    id: 'passive',
    name: 'Passive Voice',
    description: 'Detect passive constructions',
    icon: 'AlertTriangle',
    category: 'analyze',
    requiresSelection: false,
    isStreaming: false,
  },
  {
    id: 'jargon',
    name: 'Simplify Jargon',
    description: 'Replace complex terms',
    icon: 'BookOpen',
    category: 'analyze',
    requiresSelection: true,
    isStreaming: true,
  },
]

export interface ReadabilityScore {
  score: number
  grade: string
  avgSentenceLength: number
  avgWordLength: number
  suggestions: string[]
}

export interface GrammarIssue {
  offset: number
  length: number
  message: string
  replacements: string[]
  severity: 'error' | 'warning' | 'info'
}

export interface PassiveVoiceMatch {
  offset: number
  length: number
  text: string
  suggestion: string
}
