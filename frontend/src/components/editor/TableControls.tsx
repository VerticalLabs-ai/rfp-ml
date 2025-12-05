import { Editor } from '@tiptap/react'
import {
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
