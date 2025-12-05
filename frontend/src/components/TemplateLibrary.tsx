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
