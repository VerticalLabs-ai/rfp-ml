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
