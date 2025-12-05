# Proposal Copilot Enhancement - Best-in-Class Editing Experience

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the existing Proposal Copilot into a best-in-class proposal editing experience with rich text editing, AI tools toolbar, template system, real-time assistance, and professional export options.

**Architecture:** Enhance the existing TipTap-based editor with advanced extensions (tables, images, math, code blocks), add a floating AI toolbar for quick actions, implement a template library with one-click insertion, add real-time writing assistance with inline suggestions, and create export pipelines for Word/PDF with company branding.

**Tech Stack:** TipTap v3 (extended), React 18, Radix UI, docx.js (Word export), @react-pdf/renderer (PDF), KaTeX (math), Prism.js (code highlighting), Zustand (state)

---

## Phase 1: Enhanced Rich Text Editing

### Task 1: Install TipTap Extensions

**Files:**
- Modify: `frontend/package.json`

**Step 1: Add TipTap extension dependencies**

Run:
```bash
cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npm install @tiptap/extension-table @tiptap/extension-table-row @tiptap/extension-table-cell @tiptap/extension-table-header @tiptap/extension-image @tiptap/extension-code-block-lowlight @tiptap/extension-underline @tiptap/extension-text-align @tiptap/extension-highlight @tiptap/extension-typography lowlight katex
```

Expected: Packages installed successfully

**Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "deps: add TipTap extensions for tables, images, code blocks"
```

---

### Task 2: Create Extended Editor Configuration

**Files:**
- Create: `frontend/src/components/editor/editorConfig.ts`
- Test: Manual - editor loads without errors

**Step 1: Create the editor configuration file**

```typescript
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Highlight from '@tiptap/extension-highlight'
import Typography from '@tiptap/extension-typography'
import Image from '@tiptap/extension-image'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import Placeholder from '@tiptap/extension-placeholder'
import { common, createLowlight } from 'lowlight'

const lowlight = createLowlight(common)

export const getEditorExtensions = (placeholder?: string) => [
  StarterKit.configure({
    codeBlock: false, // We use CodeBlockLowlight instead
    heading: {
      levels: [1, 2, 3],
    },
  }),
  Underline,
  TextAlign.configure({
    types: ['heading', 'paragraph'],
  }),
  Highlight.configure({
    multicolor: true,
  }),
  Typography,
  Image.configure({
    inline: true,
    allowBase64: true,
  }),
  Table.configure({
    resizable: true,
  }),
  TableRow,
  TableCell,
  TableHeader,
  CodeBlockLowlight.configure({
    lowlight,
  }),
  Placeholder.configure({
    placeholder: placeholder || 'Start writing or use / for commands...',
  }),
]

export { lowlight }
```

**Step 2: Verify file was created**

Run: `ls -la /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend/src/components/editor/`
Expected: `editorConfig.ts` exists

**Step 3: Commit**

```bash
git add frontend/src/components/editor/editorConfig.ts
git commit -m "feat(editor): add extended TipTap configuration with tables, images, code blocks"
```

---

### Task 3: Create Enhanced Formatting Toolbar Component

**Files:**
- Create: `frontend/src/components/editor/FormattingToolbar.tsx`

**Step 1: Create the formatting toolbar component**

```typescript
import { Editor } from '@tiptap/react'
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  Code,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Quote,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  Table,
  Image,
  Highlighter,
  Undo,
  Redo,
  FileCode,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

interface FormattingToolbarProps {
  editor: Editor | null
  onInsertImage?: () => void
  onInsertTable?: () => void
  className?: string
}

interface ToolbarButtonProps {
  onClick: () => void
  isActive?: boolean
  disabled?: boolean
  tooltip: string
  shortcut?: string
  children: React.ReactNode
}

function ToolbarButton({
  onClick,
  isActive,
  disabled,
  tooltip,
  shortcut,
  children,
}: ToolbarButtonProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClick}
            disabled={disabled}
            className={cn(
              'h-8 w-8 p-0',
              isActive && 'bg-muted text-primary'
            )}
          >
            {children}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="flex items-center gap-2">
          <span>{tooltip}</span>
          {shortcut && (
            <kbd className="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs font-mono">
              {shortcut}
            </kbd>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export function FormattingToolbar({
  editor,
  onInsertImage,
  onInsertTable,
  className,
}: FormattingToolbarProps) {
  if (!editor) return null

  const insertTable = () => {
    editor
      .chain()
      .focus()
      .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
      .run()
    onInsertTable?.()
  }

  const insertImage = () => {
    const url = window.prompt('Enter image URL:')
    if (url) {
      editor.chain().focus().setImage({ src: url }).run()
    }
    onInsertImage?.()
  }

  const insertCodeBlock = () => {
    editor.chain().focus().toggleCodeBlock().run()
  }

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-0.5 rounded-lg border bg-background p-1',
        className
      )}
    >
      {/* Text Formatting */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        isActive={editor.isActive('bold')}
        tooltip="Bold"
        shortcut="⌘B"
      >
        <Bold className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        isActive={editor.isActive('italic')}
        tooltip="Italic"
        shortcut="⌘I"
      >
        <Italic className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        isActive={editor.isActive('underline')}
        tooltip="Underline"
        shortcut="⌘U"
      >
        <Underline className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleStrike().run()}
        isActive={editor.isActive('strike')}
        tooltip="Strikethrough"
      >
        <Strikethrough className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleHighlight().run()}
        isActive={editor.isActive('highlight')}
        tooltip="Highlight"
      >
        <Highlighter className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleCode().run()}
        isActive={editor.isActive('code')}
        tooltip="Inline Code"
      >
        <Code className="h-4 w-4" />
      </ToolbarButton>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* Headings */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 gap-1 px-2">
            <Heading1 className="h-4 w-4" />
            <span className="text-xs">Heading</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 1 }).run()
            }
          >
            <Heading1 className="mr-2 h-4 w-4" />
            Heading 1
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 2 }).run()
            }
          >
            <Heading2 className="mr-2 h-4 w-4" />
            Heading 2
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 3 }).run()
            }
          >
            <Heading3 className="mr-2 h-4 w-4" />
            Heading 3
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* Lists */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        isActive={editor.isActive('bulletList')}
        tooltip="Bullet List"
      >
        <List className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        isActive={editor.isActive('orderedList')}
        tooltip="Numbered List"
      >
        <ListOrdered className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        isActive={editor.isActive('blockquote')}
        tooltip="Quote"
      >
        <Quote className="h-4 w-4" />
      </ToolbarButton>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* Alignment */}
      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign('left').run()}
        isActive={editor.isActive({ textAlign: 'left' })}
        tooltip="Align Left"
      >
        <AlignLeft className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign('center').run()}
        isActive={editor.isActive({ textAlign: 'center' })}
        tooltip="Align Center"
      >
        <AlignCenter className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign('right').run()}
        isActive={editor.isActive({ textAlign: 'right' })}
        tooltip="Align Right"
      >
        <AlignRight className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign('justify').run()}
        isActive={editor.isActive({ textAlign: 'justify' })}
        tooltip="Justify"
      >
        <AlignJustify className="h-4 w-4" />
      </ToolbarButton>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* Insert */}
      <ToolbarButton onClick={insertTable} tooltip="Insert Table">
        <Table className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton onClick={insertImage} tooltip="Insert Image">
        <Image className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={insertCodeBlock}
        isActive={editor.isActive('codeBlock')}
        tooltip="Code Block"
      >
        <FileCode className="h-4 w-4" />
      </ToolbarButton>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* Undo/Redo */}
      <ToolbarButton
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        tooltip="Undo"
        shortcut="⌘Z"
      >
        <Undo className="h-4 w-4" />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        tooltip="Redo"
        shortcut="⌘⇧Z"
      >
        <Redo className="h-4 w-4" />
      </ToolbarButton>
    </div>
  )
}
```

**Step 2: Verify file was created**

Run: `ls -la /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend/src/components/editor/`
Expected: `FormattingToolbar.tsx` exists

**Step 3: Commit**

```bash
git add frontend/src/components/editor/FormattingToolbar.tsx
git commit -m "feat(editor): add comprehensive formatting toolbar with all controls"
```

---

### Task 4: Create Table Controls Component

**Files:**
- Create: `frontend/src/components/editor/TableControls.tsx`

**Step 1: Create table controls for row/column management**

```typescript
import { Editor } from '@tiptap/react'
import {
  Plus,
  Minus,
  Trash2,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Merge,
  Split,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Separator } from '@/components/ui/separator'

interface TableControlsProps {
  editor: Editor
}

export function TableControls({ editor }: TableControlsProps) {
  if (!editor.isActive('table')) return null

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          Table Options
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56" align="start">
        <div className="grid gap-2">
          <div className="font-medium text-sm">Rows</div>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => editor.chain().focus().addRowBefore().run()}
            >
              <ArrowUp className="mr-1 h-3 w-3" />
              Add Above
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => editor.chain().focus().addRowAfter().run()}
            >
              <ArrowDown className="mr-1 h-3 w-3" />
              Add Below
            </Button>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => editor.chain().focus().deleteRow().run()}
          >
            <Minus className="mr-1 h-3 w-3" />
            Delete Row
          </Button>

          <Separator />

          <div className="font-medium text-sm">Columns</div>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => editor.chain().focus().addColumnBefore().run()}
            >
              <ArrowLeft className="mr-1 h-3 w-3" />
              Add Left
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => editor.chain().focus().addColumnAfter().run()}
            >
              <ArrowRight className="mr-1 h-3 w-3" />
              Add Right
            </Button>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => editor.chain().focus().deleteColumn().run()}
          >
            <Minus className="mr-1 h-3 w-3" />
            Delete Column
          </Button>

          <Separator />

          <div className="font-medium text-sm">Cells</div>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => editor.chain().focus().mergeCells().run()}
            >
              <Merge className="mr-1 h-3 w-3" />
              Merge
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => editor.chain().focus().splitCell().run()}
            >
              <Split className="mr-1 h-3 w-3" />
              Split
            </Button>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => editor.chain().focus().toggleHeaderCell().run()}
          >
            Toggle Header
          </Button>

          <Separator />

          <Button
            variant="destructive"
            size="sm"
            onClick={() => editor.chain().focus().deleteTable().run()}
          >
            <Trash2 className="mr-1 h-3 w-3" />
            Delete Table
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/editor/TableControls.tsx
git commit -m "feat(editor): add table controls for row/column/cell management"
```

---

### Task 5: Create Editor Components Index

**Files:**
- Create: `frontend/src/components/editor/index.ts`

**Step 1: Create barrel export file**

```typescript
export { getEditorExtensions, lowlight } from './editorConfig'
export { FormattingToolbar } from './FormattingToolbar'
export { TableControls } from './TableControls'
```

**Step 2: Commit**

```bash
git add frontend/src/components/editor/index.ts
git commit -m "feat(editor): add barrel export for editor components"
```

---

### Task 6: Update ProposalEditor to Use Enhanced Config

**Files:**
- Modify: `frontend/src/components/ProposalEditor.tsx`

**Step 1: Update imports to use new editor config**

Replace the StarterKit and extension imports at the top of the file with:

```typescript
import { useEditor, EditorContent } from '@tiptap/react'
import { BubbleMenu } from '@tiptap/react'
import { getEditorExtensions } from './editor/editorConfig'
import { FormattingToolbar } from './editor/FormattingToolbar'
import { TableControls } from './editor/TableControls'
```

**Step 2: Update useEditor hook to use getEditorExtensions**

Find the `useEditor` call and replace the `extensions` array with:

```typescript
const editor = useEditor({
  extensions: getEditorExtensions(placeholder),
  content: initialContent,
  editable: !readOnly,
  onUpdate: ({ editor }) => {
    const html = editor.getHTML()
    onChange(html)
  },
})
```

**Step 3: Add FormattingToolbar and TableControls to the component JSX**

Above the `<EditorContent>` component, add:

```typescript
<div className="sticky top-0 z-10 bg-background pb-2">
  <FormattingToolbar editor={editor} />
  {editor?.isActive('table') && <TableControls editor={editor} />}
</div>
```

**Step 4: Verify changes compile**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npm run build`
Expected: Build completes without errors

**Step 5: Commit**

```bash
git add frontend/src/components/ProposalEditor.tsx
git commit -m "feat(editor): integrate enhanced formatting toolbar and table controls"
```

---

## Phase 2: AI Tools Toolbar

### Task 7: Create AI Toolbar Types

**Files:**
- Create: `frontend/src/types/aiToolbar.ts`

**Step 1: Create type definitions for AI toolbar**

```typescript
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
```

**Step 2: Commit**

```bash
git add frontend/src/types/aiToolbar.ts
git commit -m "feat(ai-toolbar): add type definitions for AI actions"
```

---

### Task 8: Create AI Tools Floating Toolbar

**Files:**
- Create: `frontend/src/components/editor/AIToolbar.tsx`

**Step 1: Create the floating AI toolbar component**

```typescript
import { useState, useCallback } from 'react'
import { Editor } from '@tiptap/react'
import {
  Sparkles,
  Maximize2,
  Minimize2,
  Briefcase,
  SpellCheck,
  Eye,
  AlertTriangle,
  BookOpen,
  Loader2,
  X,
  Check,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { AIActionId, AI_ACTIONS, ReadabilityScore } from '@/types/aiToolbar'

const iconMap = {
  Sparkles,
  Maximize2,
  Minimize2,
  Briefcase,
  SpellCheck,
  Eye,
  AlertTriangle,
  BookOpen,
}

interface AIToolbarProps {
  editor: Editor | null
  rfpId: string
  sectionId: string
  onExecuteAction: (
    actionId: AIActionId,
    selectedText: string,
    fullContent: string
  ) => Promise<string>
  className?: string
}

export function AIToolbar({
  editor,
  rfpId,
  sectionId,
  onExecuteAction,
  className,
}: AIToolbarProps) {
  const [activeAction, setActiveAction] = useState<AIActionId | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [readabilityScore, setReadabilityScore] =
    useState<ReadabilityScore | null>(null)

  const getSelectedText = useCallback(() => {
    if (!editor) return ''
    const { from, to } = editor.state.selection
    return editor.state.doc.textBetween(from, to, ' ')
  }, [editor])

  const getFullContent = useCallback(() => {
    if (!editor) return ''
    return editor.getText()
  }, [editor])

  const handleAction = async (actionId: AIActionId) => {
    if (!editor || isProcessing) return

    const action = AI_ACTIONS.find((a) => a.id === actionId)
    if (!action) return

    const selectedText = getSelectedText()
    if (action.requiresSelection && !selectedText) {
      // Show toast or feedback that selection is required
      return
    }

    setActiveAction(actionId)
    setIsProcessing(true)
    setResult(null)

    try {
      const response = await onExecuteAction(
        actionId,
        selectedText,
        getFullContent()
      )
      setResult(response)

      if (actionId === 'readability') {
        // Parse readability response
        try {
          setReadabilityScore(JSON.parse(response))
        } catch {
          setReadabilityScore(null)
        }
      }
    } catch (error) {
      console.error('AI action failed:', error)
      setResult('Error processing request. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const applyResult = () => {
    if (!editor || !result || !activeAction) return

    const action = AI_ACTIONS.find((a) => a.id === activeAction)
    if (!action || action.category === 'analyze') return

    const { from, to } = editor.state.selection
    editor
      .chain()
      .focus()
      .deleteRange({ from, to })
      .insertContent(result)
      .run()

    setResult(null)
    setActiveAction(null)
  }

  const cancelResult = () => {
    setResult(null)
    setActiveAction(null)
  }

  const hasSelection = getSelectedText().length > 0

  return (
    <div
      className={cn(
        'flex items-center gap-1 rounded-lg border bg-background/95 p-1 shadow-lg backdrop-blur',
        className
      )}
    >
      <TooltipProvider delayDuration={300}>
        {/* Transform Actions */}
        <div className="flex items-center gap-0.5">
          {AI_ACTIONS.filter((a) => a.category === 'transform').map(
            (action) => {
              const Icon = iconMap[action.icon as keyof typeof iconMap]
              const isActive = activeAction === action.id
              const isDisabled =
                isProcessing || (action.requiresSelection && !hasSelection)

              return (
                <Tooltip key={action.id}>
                  <TooltipTrigger asChild>
                    <Button
                      variant={isActive ? 'secondary' : 'ghost'}
                      size="sm"
                      className="h-8 w-8 p-0"
                      disabled={isDisabled}
                      onClick={() => handleAction(action.id)}
                    >
                      {isActive && isProcessing ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="font-medium">{action.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {action.description}
                    </p>
                    {action.requiresSelection && !hasSelection && (
                      <p className="text-xs text-yellow-500">
                        Select text first
                      </p>
                    )}
                  </TooltipContent>
                </Tooltip>
              )
            }
          )}
        </div>

        <div className="mx-1 h-6 w-px bg-border" />

        {/* Analyze Actions */}
        <div className="flex items-center gap-0.5">
          {AI_ACTIONS.filter((a) => a.category === 'analyze').map((action) => {
            const Icon = iconMap[action.icon as keyof typeof iconMap]
            const isActive = activeAction === action.id
            const isDisabled =
              isProcessing || (action.requiresSelection && !hasSelection)

            return (
              <Popover key={action.id}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <PopoverTrigger asChild>
                      <Button
                        variant={isActive ? 'secondary' : 'ghost'}
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={isDisabled}
                        onClick={() => handleAction(action.id)}
                      >
                        {isActive && isProcessing ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Icon className="h-4 w-4" />
                        )}
                      </Button>
                    </PopoverTrigger>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="font-medium">{action.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {action.description}
                    </p>
                  </TooltipContent>
                </Tooltip>

                {action.id === 'readability' && readabilityScore && (
                  <PopoverContent className="w-72">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">Readability Score</span>
                        <Badge
                          variant={
                            readabilityScore.score >= 60
                              ? 'default'
                              : 'destructive'
                          }
                        >
                          {readabilityScore.score}/100
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <p>Grade Level: {readabilityScore.grade}</p>
                        <p>
                          Avg Sentence: {readabilityScore.avgSentenceLength}{' '}
                          words
                        </p>
                        <p>Avg Word: {readabilityScore.avgWordLength} chars</p>
                      </div>
                      {readabilityScore.suggestions.length > 0 && (
                        <div>
                          <p className="mb-1 text-sm font-medium">
                            Suggestions:
                          </p>
                          <ul className="list-inside list-disc text-sm text-muted-foreground">
                            {readabilityScore.suggestions.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </PopoverContent>
                )}
              </Popover>
            )
          })}
        </div>
      </TooltipProvider>

      {/* Result Preview */}
      {result &&
        activeAction &&
        AI_ACTIONS.find((a) => a.id === activeAction)?.category ===
          'transform' && (
          <Popover open={!!result} onOpenChange={() => cancelResult()}>
            <PopoverContent className="w-96" align="end">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">AI Suggestion</span>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={() => handleAction(activeAction)}
                    >
                      <RefreshCw className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={cancelResult}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                <ScrollArea className="h-32">
                  <p className="text-sm">{result}</p>
                </ScrollArea>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={cancelResult}>
                    Cancel
                  </Button>
                  <Button size="sm" onClick={applyResult}>
                    <Check className="mr-1 h-3 w-3" />
                    Apply
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        )}
    </div>
  )
}
```

**Step 2: Update editor index to export AIToolbar**

Add to `frontend/src/components/editor/index.ts`:

```typescript
export { AIToolbar } from './AIToolbar'
```

**Step 3: Commit**

```bash
git add frontend/src/components/editor/AIToolbar.tsx frontend/src/components/editor/index.ts
git commit -m "feat(ai-toolbar): add floating AI tools toolbar with transform/analyze actions"
```

---

### Task 9: Add AI Action Backend Endpoint

**Files:**
- Modify: `api/app/routes/copilot.py`

**Step 1: Add AI action endpoint after existing command endpoint**

Add this endpoint after the `execute_command` function (around line 531):

```python
@router.post("/{rfp_id}/ai-action")
async def execute_ai_action(
    rfp_id: int,
    request: dict,
    db: Session = Depends(get_db),
):
    """Execute an AI-powered text transformation or analysis action."""
    action_id = request.get("action_id")
    selected_text = request.get("selected_text", "")
    full_content = request.get("full_content", "")

    # Validate action
    valid_actions = [
        "improve", "expand", "simplify", "formalize",
        "grammar", "readability", "passive", "jargon"
    ]
    if action_id not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action_id}")

    # Get RFP context
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Build prompts based on action
    prompts = {
        "improve": f"""Improve the following text for clarity, impact, and professionalism.
Keep the same meaning but make it more compelling for a government proposal:

Text to improve:
{selected_text}

Return only the improved text, no explanations.""",

        "expand": f"""Expand the following text with more detail and supporting information.
Add relevant technical details and professional language suitable for a government proposal:

Text to expand:
{selected_text}

Return only the expanded text, no explanations.""",

        "simplify": f"""Simplify the following text to make it easier to understand.
Use clearer language while maintaining professionalism:

Text to simplify:
{selected_text}

Return only the simplified text, no explanations.""",

        "formalize": f"""Rewrite the following text in formal government proposal language.
Use professional, official tone appropriate for federal contracts:

Text to formalize:
{selected_text}

Return only the formalized text, no explanations.""",

        "grammar": f"""Analyze the following text for grammar and spelling errors.
Return a JSON array of issues with this structure:
[{{"offset": number, "length": number, "message": "description", "replacements": ["suggestion1"], "severity": "error|warning|info"}}]

Text to analyze:
{full_content}""",

        "readability": f"""Analyze the readability of the following text.
Return a JSON object with this structure:
{{"score": 0-100, "grade": "Grade level", "avgSentenceLength": number, "avgWordLength": number, "suggestions": ["suggestion1", "suggestion2"]}}

Text to analyze:
{full_content}""",

        "passive": f"""Find all passive voice constructions in the following text.
Return a JSON array with this structure:
[{{"offset": number, "length": number, "text": "passive phrase", "suggestion": "active alternative"}}]

Text to analyze:
{full_content}""",

        "jargon": f"""Identify and simplify jargon and complex terms in the following text.
Replace technical jargon with clearer alternatives while maintaining accuracy:

Text to simplify:
{selected_text}

Return only the simplified text, no explanations.""",
    }

    prompt = prompts.get(action_id, "")

    try:
        import anthropic
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text
        return {"result": result, "action": action_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Verify server still starts**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml && docker-compose logs api --tail=20`
Expected: No startup errors

**Step 3: Commit**

```bash
git add api/app/routes/copilot.py
git commit -m "feat(api): add AI action endpoint for text transformations and analysis"
```

---

### Task 10: Add AI Action API Client Method

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add executeAIAction method to copilot object**

Find the `copilot` object in the API service and add this method:

```typescript
executeAIAction: async (
  rfpId: number,
  actionId: string,
  selectedText: string,
  fullContent: string
): Promise<{ result: string; action: string }> => {
  const response = await apiClient.post(`/copilot/${rfpId}/ai-action`, {
    action_id: actionId,
    selected_text: selectedText,
    full_content: fullContent,
  })
  return response.data
},
```

**Step 2: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): add executeAIAction client method"
```

---

## Phase 3: Template System

### Task 11: Create Template Types

**Files:**
- Create: `frontend/src/types/templates.ts`

**Step 1: Create template type definitions**

```typescript
export interface SectionTemplate {
  id: string
  name: string
  description: string
  category: 'executive' | 'technical' | 'management' | 'pricing' | 'compliance' | 'general'
  sectionType: string
  content: string
  variables: TemplateVariable[]
  tags: string[]
  isBoilerplate: boolean
  createdAt: string
  updatedAt: string
}

export interface TemplateVariable {
  key: string
  label: string
  defaultValue: string
  required: boolean
}

export interface TemplateCategory {
  id: string
  name: string
  icon: string
  description: string
}

export const TEMPLATE_CATEGORIES: TemplateCategory[] = [
  {
    id: 'executive',
    name: 'Executive Summary',
    icon: 'FileText',
    description: 'Opening statements and value propositions',
  },
  {
    id: 'technical',
    name: 'Technical Approach',
    icon: 'Code',
    description: 'Methodology and implementation details',
  },
  {
    id: 'management',
    name: 'Management',
    icon: 'Users',
    description: 'Team structure and project management',
  },
  {
    id: 'pricing',
    name: 'Pricing',
    icon: 'DollarSign',
    description: 'Cost narratives and pricing justification',
  },
  {
    id: 'compliance',
    name: 'Compliance',
    icon: 'Shield',
    description: 'Regulatory and contractual compliance',
  },
  {
    id: 'general',
    name: 'General',
    icon: 'Folder',
    description: 'Reusable boilerplate content',
  },
]

// Default templates for initial setup
export const DEFAULT_TEMPLATES: Omit<SectionTemplate, 'id' | 'createdAt' | 'updatedAt'>[] = [
  {
    name: 'Standard Executive Summary',
    description: 'Professional executive summary with value proposition',
    category: 'executive',
    sectionType: 'executive_summary',
    content: `## Executive Summary

{{company_name}} is pleased to submit this proposal in response to {{rfp_title}}. With {{years_experience}} years of experience in {{industry}}, we are uniquely positioned to deliver exceptional results.

### Our Understanding
We understand the critical importance of this initiative and have carefully analyzed the requirements to develop a comprehensive solution that addresses your needs.

### Value Proposition
- Proven track record with similar engagements
- Dedicated team of certified professionals
- Innovative approach combining best practices with cutting-edge technology
- Commitment to exceeding performance standards

### Why {{company_name}}
Our approach is built on a foundation of {{core_competency}}, ensuring that we deliver measurable results on time and within budget.`,
    variables: [
      { key: 'company_name', label: 'Company Name', defaultValue: '', required: true },
      { key: 'rfp_title', label: 'RFP Title', defaultValue: '', required: true },
      { key: 'years_experience', label: 'Years of Experience', defaultValue: '15', required: false },
      { key: 'industry', label: 'Industry', defaultValue: 'government contracting', required: false },
      { key: 'core_competency', label: 'Core Competency', defaultValue: 'technical excellence', required: false },
    ],
    tags: ['standard', 'federal', 'professional'],
    isBoilerplate: false,
  },
  {
    name: 'Technical Methodology',
    description: 'Standard technical approach with phased implementation',
    category: 'technical',
    sectionType: 'technical_approach',
    content: `## Technical Approach

### Methodology Overview
Our technical approach follows industry-recognized methodologies adapted for {{agency_type}} requirements. We employ an iterative, risk-managed approach that ensures continuous delivery of value.

### Phase 1: Discovery & Planning
- Requirements validation and gap analysis
- Stakeholder interviews and workshops
- Technical architecture design
- Risk assessment and mitigation planning

### Phase 2: Development & Implementation
- Agile development sprints with bi-weekly demonstrations
- Continuous integration and automated testing
- Security and compliance validation
- User acceptance testing

### Phase 3: Deployment & Transition
- Staged rollout with pilot programs
- Knowledge transfer and documentation
- Training delivery
- Post-deployment support

### Quality Assurance
All deliverables undergo rigorous quality checks aligned with {{quality_standard}} standards.`,
    variables: [
      { key: 'agency_type', label: 'Agency Type', defaultValue: 'federal', required: false },
      { key: 'quality_standard', label: 'Quality Standard', defaultValue: 'ISO 9001', required: false },
    ],
    tags: ['technical', 'methodology', 'agile'],
    isBoilerplate: false,
  },
  {
    name: 'Company Capabilities',
    description: 'Standard company qualifications boilerplate',
    category: 'general',
    sectionType: 'company_qualifications',
    content: `## Company Qualifications

### About {{company_name}}
{{company_name}} is a {{company_type}} specializing in {{specialization}}. Established in {{established_year}}, we have grown to {{employee_count}} employees serving clients across {{service_regions}}.

### Certifications & Clearances
{{#certifications}}
- {{.}}
{{/certifications}}

### Contract Vehicles
{{#contract_vehicles}}
- {{.}}
{{/contract_vehicles}}

### Core Competencies
{{#competencies}}
- {{.}}
{{/competencies}}`,
    variables: [
      { key: 'company_name', label: 'Company Name', defaultValue: '', required: true },
      { key: 'company_type', label: 'Company Type', defaultValue: 'small business', required: false },
      { key: 'specialization', label: 'Specialization', defaultValue: 'IT services', required: false },
      { key: 'established_year', label: 'Year Established', defaultValue: '2010', required: false },
      { key: 'employee_count', label: 'Employee Count', defaultValue: '50', required: false },
      { key: 'service_regions', label: 'Service Regions', defaultValue: 'the federal government', required: false },
    ],
    tags: ['boilerplate', 'qualifications', 'company'],
    isBoilerplate: true,
  },
]
```

**Step 2: Commit**

```bash
git add frontend/src/types/templates.ts
git commit -m "feat(templates): add template type definitions and default templates"
```

---

### Task 12: Create Template Library Component

**Files:**
- Create: `frontend/src/components/TemplateLibrary.tsx`

**Step 1: Create the template library component**

```typescript
import { useState, useMemo } from 'react'
import {
  FileText,
  Code,
  Users,
  DollarSign,
  Shield,
  Folder,
  Search,
  Plus,
  Copy,
  ChevronRight,
  Tag,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import {
  SectionTemplate,
  TemplateVariable,
  TEMPLATE_CATEGORIES,
  DEFAULT_TEMPLATES,
} from '@/types/templates'

const iconMap = {
  FileText,
  Code,
  Users,
  DollarSign,
  Shield,
  Folder,
}

interface TemplateLibraryProps {
  onInsert: (content: string) => void
  currentSection?: string
  className?: string
}

export function TemplateLibrary({
  onInsert,
  currentSection,
  className,
}: TemplateLibraryProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] =
    useState<SectionTemplate | null>(null)
  const [variableValues, setVariableValues] = useState<Record<string, string>>(
    {}
  )
  const [showVariableDialog, setShowVariableDialog] = useState(false)

  // Convert default templates to full SectionTemplate format
  const templates: SectionTemplate[] = useMemo(
    () =>
      DEFAULT_TEMPLATES.map((t, i) => ({
        ...t,
        id: `default-${i}`,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })),
    []
  )

  const filteredTemplates = useMemo(() => {
    let result = templates

    if (selectedCategory) {
      result = result.filter((t) => t.category === selectedCategory)
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.tags.some((tag) => tag.toLowerCase().includes(query))
      )
    }

    // Prioritize templates matching current section
    if (currentSection) {
      result.sort((a, b) => {
        const aMatch = a.sectionType === currentSection ? -1 : 0
        const bMatch = b.sectionType === currentSection ? -1 : 0
        return aMatch - bMatch
      })
    }

    return result
  }, [templates, selectedCategory, searchQuery, currentSection])

  const handleSelectTemplate = (template: SectionTemplate) => {
    setSelectedTemplate(template)
    // Initialize variable values with defaults
    const initialValues: Record<string, string> = {}
    template.variables.forEach((v) => {
      initialValues[v.key] = v.defaultValue
    })
    setVariableValues(initialValues)

    if (template.variables.length > 0) {
      setShowVariableDialog(true)
    } else {
      onInsert(template.content)
    }
  }

  const handleInsertWithVariables = () => {
    if (!selectedTemplate) return

    let content = selectedTemplate.content
    selectedTemplate.variables.forEach((v) => {
      const value = variableValues[v.key] || v.defaultValue
      content = content.replace(new RegExp(`{{${v.key}}}`, 'g'), value)
    })

    onInsert(content)
    setShowVariableDialog(false)
    setSelectedTemplate(null)
    setVariableValues({})
  }

  return (
    <div className={cn('flex h-full flex-col', className)}>
      {/* Search */}
      <div className="mb-4 flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      {/* Categories */}
      <div className="mb-4 flex flex-wrap gap-2">
        <Button
          variant={selectedCategory === null ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedCategory(null)}
        >
          All
        </Button>
        {TEMPLATE_CATEGORIES.map((cat) => {
          const Icon = iconMap[cat.icon as keyof typeof iconMap]
          return (
            <Button
              key={cat.id}
              variant={selectedCategory === cat.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(cat.id)}
            >
              <Icon className="mr-1 h-3 w-3" />
              {cat.name}
            </Button>
          )
        })}
      </div>

      {/* Template List */}
      <ScrollArea className="flex-1">
        <Accordion type="single" collapsible className="w-full">
          {filteredTemplates.map((template) => (
            <AccordionItem key={template.id} value={template.id}>
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-2 text-left">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{template.name}</span>
                      {template.isBoilerplate && (
                        <Badge variant="secondary" className="text-xs">
                          Boilerplate
                        </Badge>
                      )}
                      {template.sectionType === currentSection && (
                        <Badge variant="default" className="text-xs">
                          Recommended
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {template.description}
                    </p>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-3">
                  {/* Tags */}
                  <div className="flex flex-wrap gap-1">
                    {template.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        <Tag className="mr-1 h-2 w-2" />
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  {/* Preview */}
                  <div className="rounded-md bg-muted/50 p-3">
                    <pre className="whitespace-pre-wrap text-xs">
                      {template.content.slice(0, 300)}
                      {template.content.length > 300 && '...'}
                    </pre>
                  </div>

                  {/* Variables indicator */}
                  {template.variables.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {template.variables.length} variable
                      {template.variables.length !== 1 ? 's' : ''} to fill in
                    </p>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleSelectTemplate(template)}
                    >
                      <Plus className="mr-1 h-3 w-3" />
                      Insert
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        navigator.clipboard.writeText(template.content)
                      }}
                    >
                      <Copy className="mr-1 h-3 w-3" />
                      Copy
                    </Button>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>

        {filteredTemplates.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Folder className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No templates found matching your criteria
            </p>
          </div>
        )}
      </ScrollArea>

      {/* Variable Input Dialog */}
      <Dialog open={showVariableDialog} onOpenChange={setShowVariableDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Customize Template</DialogTitle>
            <DialogDescription>
              Fill in the values below to personalize this template.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {selectedTemplate?.variables.map((variable) => (
              <div key={variable.key} className="grid gap-2">
                <Label htmlFor={variable.key}>
                  {variable.label}
                  {variable.required && (
                    <span className="ml-1 text-destructive">*</span>
                  )}
                </Label>
                <Input
                  id={variable.key}
                  value={variableValues[variable.key] || ''}
                  onChange={(e) =>
                    setVariableValues((prev) => ({
                      ...prev,
                      [variable.key]: e.target.value,
                    }))
                  }
                  placeholder={variable.defaultValue || `Enter ${variable.label.toLowerCase()}`}
                />
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowVariableDialog(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleInsertWithVariables}>
              <ChevronRight className="mr-1 h-4 w-4" />
              Insert Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/TemplateLibrary.tsx
git commit -m "feat(templates): add template library component with search, categories, and variables"
```

---

## Phase 4: Real-time Assistance

### Task 13: Create Writing Stats Component

**Files:**
- Create: `frontend/src/components/editor/WritingStats.tsx`

**Step 1: Create writing statistics component**

```typescript
import { useMemo } from 'react'
import { FileText, Clock, Target, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

interface WritingStatsProps {
  content: string
  sectionType: string
  targetWordCount?: number
  className?: string
}

// Approximate word counts per section type
const SECTION_TARGETS: Record<string, { min: number; target: number; max: number }> = {
  executive_summary: { min: 300, target: 500, max: 750 },
  technical_approach: { min: 800, target: 1500, max: 2500 },
  company_qualifications: { min: 400, target: 700, max: 1000 },
  management_approach: { min: 500, target: 800, max: 1200 },
  pricing_narrative: { min: 300, target: 500, max: 800 },
  past_performance: { min: 600, target: 1000, max: 1500 },
  staffing_plan: { min: 400, target: 600, max: 900 },
  quality_assurance: { min: 300, target: 500, max: 800 },
  risk_mitigation: { min: 300, target: 500, max: 800 },
  compliance_matrix: { min: 200, target: 400, max: 600 },
}

// Average reading speed (words per minute)
const READING_SPEED = 200
// Average words per page (single-spaced, standard margins)
const WORDS_PER_PAGE = 500

export function WritingStats({
  content,
  sectionType,
  targetWordCount,
  className,
}: WritingStatsProps) {
  const stats = useMemo(() => {
    const text = content.replace(/<[^>]*>/g, ' ').trim()
    const words = text.split(/\s+/).filter((w) => w.length > 0)
    const wordCount = words.length
    const charCount = text.length
    const sentences = text.split(/[.!?]+/).filter((s) => s.trim().length > 0)
    const paragraphs = text.split(/\n\n+/).filter((p) => p.trim().length > 0)

    const avgWordLength = charCount / Math.max(wordCount, 1)
    const avgSentenceLength = wordCount / Math.max(sentences.length, 1)
    const readingTime = Math.ceil(wordCount / READING_SPEED)
    const pageEstimate = (wordCount / WORDS_PER_PAGE).toFixed(1)

    // Get target for section type
    const targets = SECTION_TARGETS[sectionType] || { min: 200, target: 500, max: 1000 }
    const effectiveTarget = targetWordCount || targets.target

    // Calculate progress
    const progress = Math.min((wordCount / effectiveTarget) * 100, 100)

    // Determine status
    let status: 'under' | 'good' | 'over' = 'under'
    if (wordCount >= targets.min && wordCount <= targets.max) {
      status = 'good'
    } else if (wordCount > targets.max) {
      status = 'over'
    }

    return {
      wordCount,
      charCount,
      sentences: sentences.length,
      paragraphs: paragraphs.length,
      avgWordLength: avgWordLength.toFixed(1),
      avgSentenceLength: avgSentenceLength.toFixed(1),
      readingTime,
      pageEstimate,
      progress,
      status,
      targets,
      effectiveTarget,
    }
  }, [content, sectionType, targetWordCount])

  const statusColors = {
    under: 'text-yellow-500',
    good: 'text-green-500',
    over: 'text-red-500',
  }

  const statusLabels = {
    under: 'Below target',
    good: 'On target',
    over: 'Over limit',
  }

  return (
    <TooltipProvider>
      <div
        className={cn(
          'flex flex-wrap items-center gap-4 text-sm text-muted-foreground',
          className
        )}
      >
        {/* Word Count */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5">
              <FileText className="h-4 w-4" />
              <span className={cn('font-medium', statusColors[stats.status])}>
                {stats.wordCount.toLocaleString()}
              </span>
              <span>/ {stats.effectiveTarget.toLocaleString()} words</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              <p className="font-medium">{statusLabels[stats.status]}</p>
              <p>
                Target: {stats.targets.min} - {stats.targets.max} words
              </p>
              <p>{stats.charCount.toLocaleString()} characters</p>
              <p>{stats.sentences} sentences</p>
              <p>{stats.paragraphs} paragraphs</p>
            </div>
          </TooltipContent>
        </Tooltip>

        {/* Progress Bar */}
        <div className="w-24">
          <Progress
            value={stats.progress}
            className={cn(
              'h-2',
              stats.status === 'under' && '[&>div]:bg-yellow-500',
              stats.status === 'good' && '[&>div]:bg-green-500',
              stats.status === 'over' && '[&>div]:bg-red-500'
            )}
          />
        </div>

        {/* Reading Time */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              <span>{stats.readingTime} min read</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>Estimated reading time at {READING_SPEED} words/min</p>
          </TooltipContent>
        </Tooltip>

        {/* Page Estimate */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5">
              <Target className="h-4 w-4" />
              <span>~{stats.pageEstimate} pages</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>
              Estimated at {WORDS_PER_PAGE} words/page (single-spaced)
            </p>
          </TooltipContent>
        </Tooltip>

        {/* Status Badge */}
        <Badge
          variant={stats.status === 'good' ? 'default' : 'secondary'}
          className={cn(
            stats.status === 'under' && 'bg-yellow-100 text-yellow-800',
            stats.status === 'over' && 'bg-red-100 text-red-800'
          )}
        >
          {stats.status === 'under' && (
            <AlertCircle className="mr-1 h-3 w-3" />
          )}
          {Math.round(stats.progress)}% complete
        </Badge>
      </div>
    </TooltipProvider>
  )
}
```

**Step 2: Export from editor index**

Add to `frontend/src/components/editor/index.ts`:

```typescript
export { WritingStats } from './WritingStats'
```

**Step 3: Commit**

```bash
git add frontend/src/components/editor/WritingStats.tsx frontend/src/components/editor/index.ts
git commit -m "feat(editor): add writing stats component with word count, page estimate, reading time"
```

---

### Task 14: Create Requirement Coverage Indicator

**Files:**
- Create: `frontend/src/components/editor/RequirementCoverage.tsx`

**Step 1: Create requirement coverage component**

```typescript
import { useMemo } from 'react'
import { CheckCircle2, Circle, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Requirement {
  id: string
  text: string
  keywords: string[]
  priority: 'must' | 'should' | 'may'
}

interface RequirementCoverageProps {
  content: string
  requirements: Requirement[]
  className?: string
}

export function RequirementCoverage({
  content,
  requirements,
  className,
}: RequirementCoverageProps) {
  const coverage = useMemo(() => {
    const normalizedContent = content.toLowerCase()

    return requirements.map((req) => {
      const matches = req.keywords.filter((kw) =>
        normalizedContent.includes(kw.toLowerCase())
      )
      const covered = matches.length >= Math.ceil(req.keywords.length * 0.5)
      const partialCoverage = matches.length / req.keywords.length

      return {
        ...req,
        covered,
        partialCoverage,
        matchedKeywords: matches,
        missingKeywords: req.keywords.filter((kw) => !matches.includes(kw)),
      }
    })
  }, [content, requirements])

  const stats = useMemo(() => {
    const covered = coverage.filter((r) => r.covered).length
    const mustRequirements = coverage.filter((r) => r.priority === 'must')
    const mustCovered = mustRequirements.filter((r) => r.covered).length

    return {
      total: coverage.length,
      covered,
      percentage: Math.round((covered / Math.max(coverage.length, 1)) * 100),
      mustTotal: mustRequirements.length,
      mustCovered,
      mustPercentage: Math.round(
        (mustCovered / Math.max(mustRequirements.length, 1)) * 100
      ),
    }
  }, [coverage])

  const priorityIcons = {
    must: <AlertCircle className="h-3 w-3 text-red-500" />,
    should: <Circle className="h-3 w-3 text-yellow-500" />,
    may: <Circle className="h-3 w-3 text-blue-500" />,
  }

  return (
    <TooltipProvider>
      <div className={cn('space-y-3', className)}>
        {/* Summary */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Requirement Coverage</span>
            <Badge variant={stats.percentage >= 80 ? 'default' : 'secondary'}>
              {stats.covered}/{stats.total}
            </Badge>
          </div>
          <Tooltip>
            <TooltipTrigger>
              <Badge
                variant={stats.mustPercentage >= 100 ? 'default' : 'destructive'}
              >
                {stats.mustCovered}/{stats.mustTotal} Must-Have
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p>
                {stats.mustPercentage}% of mandatory requirements addressed
              </p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Progress */}
        <Progress
          value={stats.percentage}
          className={cn(
            'h-2',
            stats.percentage < 50 && '[&>div]:bg-red-500',
            stats.percentage >= 50 &&
              stats.percentage < 80 &&
              '[&>div]:bg-yellow-500',
            stats.percentage >= 80 && '[&>div]:bg-green-500'
          )}
        />

        {/* Detailed List */}
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full justify-between">
              View Requirements
              <ChevronDown className="h-4 w-4" />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-2 space-y-2">
              {coverage.map((req) => (
                <div
                  key={req.id}
                  className={cn(
                    'flex items-start gap-2 rounded-md p-2 text-sm',
                    req.covered ? 'bg-green-50' : 'bg-muted'
                  )}
                >
                  {req.covered ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 text-green-500" />
                  ) : (
                    priorityIcons[req.priority]
                  )}
                  <div className="flex-1">
                    <p
                      className={cn(
                        'font-medium',
                        req.covered
                          ? 'text-green-700'
                          : 'text-muted-foreground'
                      )}
                    >
                      {req.text}
                    </p>
                    {!req.covered && req.missingKeywords.length > 0 && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Missing: {req.missingKeywords.join(', ')}
                      </p>
                    )}
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      'text-xs',
                      req.priority === 'must' && 'border-red-300 text-red-700',
                      req.priority === 'should' &&
                        'border-yellow-300 text-yellow-700',
                      req.priority === 'may' && 'border-blue-300 text-blue-700'
                    )}
                  >
                    {req.priority}
                  </Badge>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </TooltipProvider>
  )
}
```

**Step 2: Export from editor index**

Add to `frontend/src/components/editor/index.ts`:

```typescript
export { RequirementCoverage } from './RequirementCoverage'
```

**Step 3: Commit**

```bash
git add frontend/src/components/editor/RequirementCoverage.tsx frontend/src/components/editor/index.ts
git commit -m "feat(editor): add requirement coverage indicator with keyword matching"
```

---

## Phase 5: Export Options

### Task 15: Install Export Dependencies

**Files:**
- Modify: `frontend/package.json`

**Step 1: Add export library dependencies**

Run:
```bash
cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npm install docx file-saver html-to-docx @types/file-saver
```

Expected: Packages installed successfully

**Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "deps: add docx and file-saver for Word export"
```

---

### Task 16: Create Export Service

**Files:**
- Create: `frontend/src/services/exportService.ts`

**Step 1: Create the export service**

```typescript
import { saveAs } from 'file-saver'
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  AlignmentType,
  PageBreak,
  Header,
  Footer,
  ImageRun,
} from 'docx'

interface ExportSection {
  id: string
  title: string
  content: string
}

interface ExportOptions {
  filename: string
  companyName?: string
  companyLogo?: string // Base64 encoded image
  rfpTitle?: string
  includeTableOfContents?: boolean
  includeHeader?: boolean
  includeFooter?: boolean
  includePageNumbers?: boolean
}

// Convert HTML to docx paragraphs
function htmlToDocxElements(html: string): (Paragraph | Table)[] {
  const elements: (Paragraph | Table)[] = []
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')

  function processNode(node: Node): void {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent?.trim()
      if (text) {
        elements.push(
          new Paragraph({
            children: [new TextRun(text)],
          })
        )
      }
      return
    }

    if (node.nodeType !== Node.ELEMENT_NODE) return

    const el = node as Element
    const tagName = el.tagName.toLowerCase()

    switch (tagName) {
      case 'h1':
        elements.push(
          new Paragraph({
            text: el.textContent || '',
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 400, after: 200 },
          })
        )
        break

      case 'h2':
        elements.push(
          new Paragraph({
            text: el.textContent || '',
            heading: HeadingLevel.HEADING_2,
            spacing: { before: 300, after: 150 },
          })
        )
        break

      case 'h3':
        elements.push(
          new Paragraph({
            text: el.textContent || '',
            heading: HeadingLevel.HEADING_3,
            spacing: { before: 200, after: 100 },
          })
        )
        break

      case 'p':
        const runs: TextRun[] = []
        el.childNodes.forEach((child) => {
          if (child.nodeType === Node.TEXT_NODE) {
            runs.push(new TextRun(child.textContent || ''))
          } else if (child.nodeType === Node.ELEMENT_NODE) {
            const childEl = child as Element
            const text = childEl.textContent || ''
            switch (childEl.tagName.toLowerCase()) {
              case 'strong':
              case 'b':
                runs.push(new TextRun({ text, bold: true }))
                break
              case 'em':
              case 'i':
                runs.push(new TextRun({ text, italics: true }))
                break
              case 'u':
                runs.push(new TextRun({ text, underline: {} }))
                break
              case 'code':
                runs.push(new TextRun({ text, font: 'Courier New' }))
                break
              default:
                runs.push(new TextRun(text))
            }
          }
        })
        if (runs.length > 0) {
          elements.push(
            new Paragraph({
              children: runs,
              spacing: { after: 120 },
            })
          )
        }
        break

      case 'ul':
      case 'ol':
        el.querySelectorAll('li').forEach((li, index) => {
          elements.push(
            new Paragraph({
              text: `${tagName === 'ol' ? `${index + 1}.` : '•'} ${li.textContent}`,
              indent: { left: 720 },
              spacing: { after: 80 },
            })
          )
        })
        break

      case 'blockquote':
        elements.push(
          new Paragraph({
            children: [
              new TextRun({
                text: el.textContent || '',
                italics: true,
              }),
            ],
            indent: { left: 720 },
            spacing: { before: 200, after: 200 },
          })
        )
        break

      case 'table':
        const rows: TableRow[] = []
        el.querySelectorAll('tr').forEach((tr, rowIndex) => {
          const cells: TableCell[] = []
          tr.querySelectorAll('th, td').forEach((cell) => {
            cells.push(
              new TableCell({
                children: [new Paragraph(cell.textContent || '')],
                shading:
                  rowIndex === 0
                    ? { fill: 'E0E0E0', type: 'solid' as const }
                    : undefined,
              })
            )
          })
          rows.push(new TableRow({ children: cells }))
        })
        if (rows.length > 0) {
          elements.push(
            new Table({
              rows,
              width: { size: 100, type: WidthType.PERCENTAGE },
            })
          )
        }
        break

      case 'pre':
        elements.push(
          new Paragraph({
            children: [
              new TextRun({
                text: el.textContent || '',
                font: 'Courier New',
                size: 20,
              }),
            ],
            shading: { fill: 'F5F5F5', type: 'solid' as const },
            spacing: { before: 200, after: 200 },
          })
        )
        break

      default:
        // Process children for container elements
        el.childNodes.forEach(processNode)
    }
  }

  doc.body.childNodes.forEach(processNode)
  return elements
}

export async function exportToWord(
  sections: ExportSection[],
  options: ExportOptions
): Promise<void> {
  const docSections: (Paragraph | Table)[] = []

  // Title page
  docSections.push(
    new Paragraph({
      children: [new TextRun('')],
      spacing: { before: 2000 },
    })
  )

  if (options.rfpTitle) {
    docSections.push(
      new Paragraph({
        text: options.rfpTitle,
        heading: HeadingLevel.TITLE,
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
      })
    )
  }

  docSections.push(
    new Paragraph({
      text: 'PROPOSAL',
      heading: HeadingLevel.HEADING_1,
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
    })
  )

  if (options.companyName) {
    docSections.push(
      new Paragraph({
        text: `Submitted by ${options.companyName}`,
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
      })
    )
  }

  docSections.push(
    new Paragraph({
      text: new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      }),
      alignment: AlignmentType.CENTER,
    })
  )

  // Page break after title
  docSections.push(
    new Paragraph({
      children: [new PageBreak()],
    })
  )

  // Table of Contents placeholder
  if (options.includeTableOfContents) {
    docSections.push(
      new Paragraph({
        text: 'TABLE OF CONTENTS',
        heading: HeadingLevel.HEADING_1,
        spacing: { after: 400 },
      })
    )

    sections.forEach((section, index) => {
      docSections.push(
        new Paragraph({
          text: `${index + 1}. ${section.title}`,
          spacing: { after: 100 },
        })
      )
    })

    docSections.push(
      new Paragraph({
        children: [new PageBreak()],
      })
    )
  }

  // Content sections
  sections.forEach((section) => {
    // Section heading
    docSections.push(
      new Paragraph({
        text: section.title,
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 400, after: 200 },
      })
    )

    // Section content
    const contentElements = htmlToDocxElements(section.content)
    docSections.push(...contentElements)

    // Page break between sections
    docSections.push(
      new Paragraph({
        children: [new PageBreak()],
      })
    )
  })

  // Create document
  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 1440, // 1 inch in twips
              bottom: 1440,
              left: 1440,
              right: 1440,
            },
          },
        },
        headers: options.includeHeader
          ? {
              default: new Header({
                children: [
                  new Paragraph({
                    text: options.companyName || '',
                    alignment: AlignmentType.RIGHT,
                  }),
                ],
              }),
            }
          : undefined,
        footers: options.includeFooter || options.includePageNumbers
          ? {
              default: new Footer({
                children: [
                  new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                      new TextRun({
                        text: options.includePageNumbers ? 'Page ' : '',
                      }),
                    ],
                  }),
                ],
              }),
            }
          : undefined,
        children: docSections,
      },
    ],
  })

  // Generate and download
  const blob = await Packer.toBlob(doc)
  saveAs(blob, `${options.filename}.docx`)
}

export function exportToMarkdown(
  sections: ExportSection[],
  options: ExportOptions
): void {
  let markdown = ''

  // Title
  if (options.rfpTitle) {
    markdown += `# ${options.rfpTitle}\n\n`
  }

  if (options.companyName) {
    markdown += `**Submitted by:** ${options.companyName}\n\n`
  }

  markdown += `**Date:** ${new Date().toLocaleDateString()}\n\n---\n\n`

  // Table of Contents
  if (options.includeTableOfContents) {
    markdown += '## Table of Contents\n\n'
    sections.forEach((section, index) => {
      const anchor = section.title.toLowerCase().replace(/\s+/g, '-')
      markdown += `${index + 1}. [${section.title}](#${anchor})\n`
    })
    markdown += '\n---\n\n'
  }

  // Sections
  sections.forEach((section) => {
    markdown += `## ${section.title}\n\n`
    // Convert HTML to markdown (simplified)
    let content = section.content
      .replace(/<h1[^>]*>(.*?)<\/h1>/gi, '# $1\n\n')
      .replace(/<h2[^>]*>(.*?)<\/h2>/gi, '## $1\n\n')
      .replace(/<h3[^>]*>(.*?)<\/h3>/gi, '### $1\n\n')
      .replace(/<strong>(.*?)<\/strong>/gi, '**$1**')
      .replace(/<b>(.*?)<\/b>/gi, '**$1**')
      .replace(/<em>(.*?)<\/em>/gi, '*$1*')
      .replace(/<i>(.*?)<\/i>/gi, '*$1*')
      .replace(/<code>(.*?)<\/code>/gi, '`$1`')
      .replace(/<li>(.*?)<\/li>/gi, '- $1\n')
      .replace(/<blockquote>(.*?)<\/blockquote>/gi, '> $1\n')
      .replace(/<p>(.*?)<\/p>/gi, '$1\n\n')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .trim()
    markdown += content + '\n\n---\n\n'
  })

  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  saveAs(blob, `${options.filename}.md`)
}

export function exportToJSON(
  sections: ExportSection[],
  options: ExportOptions
): void {
  const data = {
    metadata: {
      rfpTitle: options.rfpTitle,
      companyName: options.companyName,
      exportedAt: new Date().toISOString(),
    },
    sections: sections.map((s) => ({
      id: s.id,
      title: s.title,
      content: s.content,
    })),
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  saveAs(blob, `${options.filename}.json`)
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/exportService.ts
git commit -m "feat(export): add export service for Word, Markdown, and JSON formats"
```

---

### Task 17: Create Export Dialog Component

**Files:**
- Create: `frontend/src/components/ExportDialog.tsx`

**Step 1: Create the export dialog component**

```typescript
import { useState } from 'react'
import {
  FileText,
  FileJson,
  FileCode,
  Download,
  Settings,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Separator } from '@/components/ui/separator'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { toast } from 'sonner'
import {
  exportToWord,
  exportToMarkdown,
  exportToJSON,
} from '@/services/exportService'

interface ExportSection {
  id: string
  title: string
  content: string
}

interface ExportDialogProps {
  sections: ExportSection[]
  rfpTitle?: string
  companyName?: string
  trigger?: React.ReactNode
}

type ExportFormat = 'docx' | 'md' | 'json'

export function ExportDialog({
  sections,
  rfpTitle,
  companyName,
  trigger,
}: ExportDialogProps) {
  const [open, setOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [format, setFormat] = useState<ExportFormat>('docx')
  const [filename, setFilename] = useState(
    rfpTitle?.toLowerCase().replace(/\s+/g, '-') || 'proposal'
  )
  const [options, setOptions] = useState({
    includeTableOfContents: true,
    includeHeader: true,
    includeFooter: true,
    includePageNumbers: true,
    customCompanyName: companyName || '',
  })
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleExport = async () => {
    if (sections.length === 0) {
      toast.error('No content to export')
      return
    }

    setIsExporting(true)

    try {
      const exportOptions = {
        filename,
        rfpTitle,
        companyName: options.customCompanyName,
        includeTableOfContents: options.includeTableOfContents,
        includeHeader: options.includeHeader,
        includeFooter: options.includeFooter,
        includePageNumbers: options.includePageNumbers,
      }

      switch (format) {
        case 'docx':
          await exportToWord(sections, exportOptions)
          break
        case 'md':
          exportToMarkdown(sections, exportOptions)
          break
        case 'json':
          exportToJSON(sections, exportOptions)
          break
      }

      toast.success(`Exported successfully as ${format.toUpperCase()}`)
      setOpen(false)
    } catch (error) {
      console.error('Export failed:', error)
      toast.error('Export failed. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }

  const formatOptions = [
    {
      value: 'docx',
      label: 'Word Document',
      description: 'Microsoft Word format with formatting',
      icon: FileText,
    },
    {
      value: 'md',
      label: 'Markdown',
      description: 'Plain text with markdown formatting',
      icon: FileCode,
    },
    {
      value: 'json',
      label: 'JSON',
      description: 'Structured data format',
      icon: FileJson,
    },
  ]

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Export Proposal</DialogTitle>
          <DialogDescription>
            Export your proposal in various formats. Word format includes full
            formatting and is recommended for submission.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Format Selection */}
          <div className="grid gap-3">
            <Label>Export Format</Label>
            <RadioGroup
              value={format}
              onValueChange={(v) => setFormat(v as ExportFormat)}
              className="grid gap-2"
            >
              {formatOptions.map((opt) => (
                <div
                  key={opt.value}
                  className={`flex items-center space-x-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                    format === opt.value
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted'
                  }`}
                  onClick={() => setFormat(opt.value as ExportFormat)}
                >
                  <RadioGroupItem value={opt.value} id={opt.value} />
                  <opt.icon className="h-5 w-5 text-muted-foreground" />
                  <div className="flex-1">
                    <Label htmlFor={opt.value} className="cursor-pointer">
                      {opt.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {opt.description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Filename */}
          <div className="grid gap-2">
            <Label htmlFor="filename">Filename</Label>
            <div className="flex">
              <Input
                id="filename"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                placeholder="proposal"
                className="rounded-r-none"
              />
              <div className="flex items-center rounded-r-md border border-l-0 bg-muted px-3 text-sm text-muted-foreground">
                .{format}
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          {format === 'docx' && (
            <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-between"
                >
                  <span className="flex items-center">
                    <Settings className="mr-2 h-4 w-4" />
                    Advanced Options
                  </span>
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-3 space-y-4">
                <Separator />

                <div className="grid gap-2">
                  <Label htmlFor="companyName">Company Name</Label>
                  <Input
                    id="companyName"
                    value={options.customCompanyName}
                    onChange={(e) =>
                      setOptions((prev) => ({
                        ...prev,
                        customCompanyName: e.target.value,
                      }))
                    }
                    placeholder="Your Company Name"
                  />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="toc">Include Table of Contents</Label>
                    <Switch
                      id="toc"
                      checked={options.includeTableOfContents}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({
                          ...prev,
                          includeTableOfContents: v,
                        }))
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="header">Include Header</Label>
                    <Switch
                      id="header"
                      checked={options.includeHeader}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({ ...prev, includeHeader: v }))
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="footer">Include Footer</Label>
                    <Switch
                      id="footer"
                      checked={options.includeFooter}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({ ...prev, includeFooter: v }))
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="pageNumbers">Include Page Numbers</Label>
                    <Switch
                      id="pageNumbers"
                      checked={options.includePageNumbers}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({
                          ...prev,
                          includePageNumbers: v,
                        }))
                      }
                    />
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Section Summary */}
          <div className="rounded-lg bg-muted p-3">
            <p className="text-sm text-muted-foreground">
              <strong>{sections.length}</strong> sections will be exported
              {sections.length > 0 && (
                <span className="ml-1">
                  ({sections.map((s) => s.title).join(', ')})
                </span>
              )}
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Export
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ExportDialog.tsx
git commit -m "feat(export): add export dialog with format selection and options"
```

---

## Phase 6: Integration

### Task 18: Update ProposalCopilot with New Components

**Files:**
- Modify: `frontend/src/pages/ProposalCopilot.tsx`

**Step 1: Add imports for new components**

At the top of the file, add these imports:

```typescript
import {
  FormattingToolbar,
  AIToolbar,
  WritingStats,
} from '@/components/editor'
import { TemplateLibrary } from '@/components/TemplateLibrary'
import { ExportDialog } from '@/components/ExportDialog'
import { api } from '@/services/api'
```

**Step 2: Add AI action handler function**

Inside the component, add this handler:

```typescript
const handleAIAction = async (
  actionId: string,
  selectedText: string,
  fullContent: string
): Promise<string> => {
  if (!rfpId) throw new Error('No RFP selected')
  const response = await api.copilot.executeAIAction(
    parseInt(rfpId),
    actionId,
    selectedText,
    fullContent
  )
  return response.result
}
```

**Step 3: Add ExportDialog to the header buttons**

Find the header area with the save/copy buttons and add:

```typescript
<ExportDialog
  sections={Object.entries(sections).map(([id, section]) => ({
    id,
    title: SECTION_LABELS[id] || id,
    content: section.content,
  }))}
  rfpTitle={rfp?.title}
  companyName={companyProfile?.company_name}
/>
```

**Step 4: Add WritingStats below the editor**

After the ProposalEditor component, add:

```typescript
<WritingStats
  content={sections[activeSection]?.content || ''}
  sectionType={activeSection}
  className="mt-2 px-4"
/>
```

**Step 5: Add AIToolbar above or alongside the editor**

Add near the formatting controls:

```typescript
<AIToolbar
  editor={editorRef.current}
  rfpId={rfpId || ''}
  sectionId={activeSection}
  onExecuteAction={handleAIAction}
  className="mb-2"
/>
```

**Step 6: Add TemplateLibrary as a collapsible panel or tab**

In the sidebar or as a new tab, add:

```typescript
<TemplateLibrary
  onInsert={(content) => {
    setSections((prev) => ({
      ...prev,
      [activeSection]: {
        ...prev[activeSection],
        content: prev[activeSection].content + '\n\n' + content,
      },
    }))
    setIsDirty(true)
  }}
  currentSection={activeSection}
/>
```

**Step 7: Verify build succeeds**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npm run build`
Expected: Build completes successfully

**Step 8: Commit**

```bash
git add frontend/src/pages/ProposalCopilot.tsx
git commit -m "feat(copilot): integrate AI toolbar, writing stats, templates, and export"
```

---

### Task 19: Add Editor Styles for Tables and Code Blocks

**Files:**
- Create: `frontend/src/styles/editor.css`

**Step 1: Create editor-specific styles**

```css
/* TipTap Editor Styles */

.ProseMirror {
  outline: none;
  min-height: 300px;
}

.ProseMirror > * + * {
  margin-top: 0.75em;
}

/* Tables */
.ProseMirror table {
  border-collapse: collapse;
  margin: 1rem 0;
  overflow: hidden;
  table-layout: fixed;
  width: 100%;
}

.ProseMirror td,
.ProseMirror th {
  border: 1px solid hsl(var(--border));
  box-sizing: border-box;
  min-width: 1em;
  padding: 0.5rem;
  position: relative;
  vertical-align: top;
}

.ProseMirror th {
  background-color: hsl(var(--muted));
  font-weight: 600;
  text-align: left;
}

.ProseMirror .selectedCell:after {
  background: hsl(var(--primary) / 0.1);
  content: '';
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  pointer-events: none;
  position: absolute;
  z-index: 2;
}

.ProseMirror .column-resize-handle {
  background-color: hsl(var(--primary));
  bottom: -2px;
  pointer-events: none;
  position: absolute;
  right: -2px;
  top: 0;
  width: 4px;
}

/* Code blocks */
.ProseMirror pre {
  background: hsl(var(--muted));
  border-radius: 0.5rem;
  font-family: 'JetBrains Mono', monospace;
  padding: 1rem;
  overflow-x: auto;
}

.ProseMirror pre code {
  background: none;
  color: inherit;
  font-size: 0.875rem;
  padding: 0;
}

/* Inline code */
.ProseMirror code {
  background-color: hsl(var(--muted));
  border-radius: 0.25rem;
  font-size: 0.875em;
  padding: 0.2em 0.4em;
}

/* Blockquotes */
.ProseMirror blockquote {
  border-left: 3px solid hsl(var(--border));
  margin: 1rem 0;
  padding-left: 1rem;
}

/* Lists */
.ProseMirror ul,
.ProseMirror ol {
  padding-left: 1.5rem;
}

.ProseMirror li {
  margin: 0.25em 0;
}

/* Headings */
.ProseMirror h1 {
  font-size: 1.875rem;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
}

.ProseMirror h2 {
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.3;
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
}

.ProseMirror h3 {
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.4;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

/* Images */
.ProseMirror img {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
}

.ProseMirror img.ProseMirror-selectednode {
  outline: 3px solid hsl(var(--primary));
}

/* Highlight */
.ProseMirror mark {
  background-color: hsl(var(--yellow-200));
  padding: 0.1em 0.2em;
  border-radius: 0.2em;
}

/* Placeholder */
.ProseMirror p.is-editor-empty:first-child::before {
  color: hsl(var(--muted-foreground));
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}

/* Text alignment */
.ProseMirror .text-left {
  text-align: left;
}

.ProseMirror .text-center {
  text-align: center;
}

.ProseMirror .text-right {
  text-align: right;
}

.ProseMirror .text-justify {
  text-align: justify;
}
```

**Step 2: Import styles in the app**

Add to `frontend/src/App.tsx` or `frontend/src/index.css`:

```css
@import './styles/editor.css';
```

**Step 3: Commit**

```bash
git add frontend/src/styles/editor.css frontend/src/index.css
git commit -m "style(editor): add TipTap editor styles for tables, code blocks, etc."
```

---

### Task 20: Final Build and Test

**Files:**
- None (verification only)

**Step 1: Run full build**

Run:
```bash
cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npm run build
```

Expected: Build completes without errors

**Step 2: Run type check**

Run:
```bash
cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit
```

Expected: No type errors

**Step 3: Start dev server and verify**

Run:
```bash
cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npm run dev
```

Expected: Dev server starts, navigate to Proposal Copilot page

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(copilot): complete best-in-class proposal editing experience

- Rich text editing with TipTap extensions (tables, images, code blocks)
- Full formatting toolbar with alignment and advanced controls
- AI tools toolbar for quick transformations (improve, expand, simplify, formalize)
- Text analysis tools (grammar, readability, passive voice, jargon)
- Template library with categories and variable substitution
- Real-time writing stats (word count, page estimate, reading time)
- Requirement coverage indicator
- Export to Word (.docx), Markdown, and JSON formats
- Professional export options (TOC, headers, footers, page numbers)"
```

---

## Summary

This plan implements a best-in-class proposal editing experience with:

1. **Rich Text Editing (Tasks 1-6):**
   - TipTap extensions for tables, images, code blocks
   - Enhanced formatting toolbar with all controls
   - Table manipulation controls

2. **AI Tools Toolbar (Tasks 7-10):**
   - Quick action buttons (Improve, Expand, Simplify, Formalize)
   - Analysis tools (Grammar, Readability, Passive Voice, Jargon)
   - Backend endpoint for AI actions

3. **Template System (Tasks 11-12):**
   - Template library with categories
   - Variable substitution
   - One-click insertion

4. **Real-time Assistance (Tasks 13-14):**
   - Writing stats (word count, page estimate, reading time)
   - Requirement coverage indicator

5. **Export Options (Tasks 15-17):**
   - Word (.docx) export with full formatting
   - Markdown export
   - JSON export
   - Advanced options (TOC, headers, footers, page numbers)

6. **Integration (Tasks 18-20):**
   - Connect all components to ProposalCopilot page
   - Editor styles
   - Final verification

**Total: 20 tasks**
