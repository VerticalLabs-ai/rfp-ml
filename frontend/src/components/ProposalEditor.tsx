import { useEffect, useRef } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import { getEditorExtensions } from './editor/editorConfig'
import { FormattingToolbar } from './editor/FormattingToolbar'
import { TableControls } from './editor/TableControls'

interface ProposalEditorProps {
  initialContent?: string
  onSave?: (content: string) => void
  readOnly?: boolean
  documentId?: string // New prop for WebSocket collaboration
}

export default function ProposalEditor({ initialContent = '', onSave, readOnly = false, documentId }: ProposalEditorProps) {
  const ws = useRef<WebSocket | null>(null)

  const editor = useEditor({
    extensions: getEditorExtensions('Start writing your proposal...'),
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
      {/* Enhanced Formatting Toolbar */}
      {!readOnly && (
        <div className="sticky top-0 z-10 bg-background pb-2">
          <FormattingToolbar editor={editor} />
          {editor?.isActive('table') && <TableControls editor={editor} />}
        </div>
      )}

      {/* Editor Content */}
      <EditorContent
        editor={editor}
        className="prose prose-slate dark:prose-invert max-w-none p-4 min-h-[300px] focus:outline-none"
      />
    </div>
  )
}