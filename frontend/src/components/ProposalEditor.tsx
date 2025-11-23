import { useEffect, useRef } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import {
  Bold, Italic, List, ListOrdered, Heading1, Heading2,
  Quote, Redo, Undo
} from 'lucide-react'
// No more api or toast imports as they are not used.

interface ProposalEditorProps {
  initialContent?: string
  onSave?: (content: string) => void
  readOnly?: boolean
  documentId?: string // New prop for WebSocket collaboration
}

export default function ProposalEditor({ initialContent = '', onSave, readOnly = false, documentId }: ProposalEditorProps) {
  const ws = useRef<WebSocket | null>(null)

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: 'Start writing your proposal...',
      }),
    ],
    content: initialContent,
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      // WebSocket functionality for collaborative editing (send updates)
      if (documentId) { // check documentId before accessing ws.current
          if (ws.current && ws.current.readyState === WebSocket.OPEN) {
              ws.current.send(JSON.stringify({
                  type: "document_update",
                  content: editor.getHTML()
              }));
          }
      }
      onSave?.(editor.getHTML());
    }
  })

  useEffect(() => {
    if (editor && initialContent) {
      // Only update if content is different to avoid loops/cursor jumps
      if (editor.getHTML() !== initialContent) {
         editor.commands.setContent(initialContent)
      }
    }
  }, [initialContent, editor])

  // WebSocket effect for real-time collaboration
  useEffect(() => {
    if (documentId && !readOnly) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const websocketUrl = `${protocol}//${host}/api/v1/ws/edit/${documentId}`

      ws.current = new WebSocket(websocketUrl)

      ws.current.onopen = () => {
        console.log(`WebSocket connected for document ${documentId}`)
      }

      ws.current.onmessage = (event) => {
        const message = JSON.parse(event.data)
        if (message.type === "initial_content" && editor) {
            editor.commands.setContent(message.content)
        } else if (message.type === "document_update" && editor) {
            if (editor.getHTML() !== message.content) {
                editor.commands.setContent(message.content)
            }
        }
      }

      ws.current.onclose = () => {
        console.log(`WebSocket disconnected for document ${documentId}`)
      }

      ws.current.onerror = (error) => {
        console.error(`WebSocket error for document ${documentId}:`, error)
      }

      return () => {
        ws.current?.close()
      }
    }
  }, [documentId, readOnly, editor])

  if (!editor) {
    return null
  }

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-white dark:bg-slate-800">
      {/* Toolbar */}
      {!readOnly && (
        <div className="border-b border-slate-200 dark:border-slate-700 p-2 flex flex-wrap gap-1 bg-slate-50 dark:bg-slate-800/50">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            isActive={editor.isActive('bold')}
            icon={<Bold className="w-4 h-4" />}
            title="Bold"
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            isActive={editor.isActive('italic')}
            icon={<Italic className="w-4 h-4" />}
            title="Italic"
          />
          <div className="w-px h-6 bg-slate-300 dark:bg-slate-600 mx-1 self-center" />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            isActive={editor.isActive('heading', { level: 1 })}
            icon={<Heading1 className="w-4 h-4" />}
            title="Heading 1"
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            isActive={editor.isActive('heading', { level: 2 })}
            icon={<Heading2 className="w-4 h-4" />}
            title="Heading 2"
          />
          <div className="w-px h-6 bg-slate-300 dark:bg-slate-600 mx-1 self-center" />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            isActive={editor.isActive('bulletList')}
            icon={<List className="w-4 h-4" />}
            title="Bullet List"
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            isActive={editor.isActive('orderedList')}
            icon={<ListOrdered className="w-4 h-4" />}
            title="Ordered List"
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            isActive={editor.isActive('blockquote')}
            icon={<Quote className="w-4 h-4" />}
            title="Quote"
          />
          <div className="w-px h-6 bg-slate-300 dark:bg-slate-600 mx-1 self-center" />
          <ToolbarButton
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            icon={<Undo className="w-4 h-4" />}
            title="Undo"
          />
          <ToolbarButton
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            icon={<Redo className="w-4 h-4" />}
            title="Redo"
          />
        </div>
      )}

      {/* Magic Bubble Menu - Temporarily removed for build */}
      {/* The AI refinement functionality will be unavailable */}

      {/* Editor Content */}
      <EditorContent
        editor={editor}
        className="prose prose-slate dark:prose-invert max-w-none p-4 min-h-[300px] focus:outline-none"
      />
    </div>
  )
}

function ToolbarButton({ onClick, isActive = false, disabled = false, icon, title }: any) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`
        p-2 rounded-md transition-colors
        ${isActive
          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      {icon}
    </button>
  )
}