/**
 * Tests for AIWriterMenu component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render, createMockWriterCommand } from '../test/test-utils'
import { AIWriterMenu } from './AIWriterMenu'

// Mock the api module
vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

// Import the mocked api
import { api } from '../lib/api'

const mockCommands = [
  createMockWriterCommand(),
  createMockWriterCommand({
    command: 'technical-approach',
    name: 'Technical Approach',
    description: 'Generate technical approach section',
    shortcut: '/tech',
  }),
]

describe('AIWriterMenu', () => {
  const defaultProps = {
    rfpId: 'RFP-2024-001',
    rfpTitle: 'IT Infrastructure Support',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // Setup default mock response for commands
    vi.mocked(api.get).mockResolvedValue({
      commands: mockCommands,
      total: mockCommands.length,
    })
  })

  it('renders the AI Writer card with title', async () => {
    render(<AIWriterMenu {...defaultProps} />)

    expect(screen.getByText('AI Writer')).toBeInTheDocument()
    expect(screen.getByText(/IT Infrastructure Support/)).toBeInTheDocument()
  })

  it('displays GovGPT Style badge', async () => {
    render(<AIWriterMenu {...defaultProps} />)

    expect(screen.getByText('GovGPT Style')).toBeInTheDocument()
  })

  it('shows command selector button', async () => {
    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    expect(button).toBeInTheDocument()
    expect(screen.getByText(/Type \/ to search commands/)).toBeInTheDocument()
  })

  it('opens command popover when clicking selector', async () => {
    const user = userEvent.setup()
    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search commands...')).toBeInTheDocument()
    })
  })

  it('displays available commands in dropdown', async () => {
    const user = userEvent.setup()
    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
      expect(screen.getByText('/tech')).toBeInTheDocument()
    })
  })

  it('shows context textarea after selecting command', async () => {
    const user = userEvent.setup()
    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    // Click on the command option
    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    await waitFor(() => {
      expect(screen.getByLabelText(/Additional Context/)).toBeInTheDocument()
    })
  })

  it('shows tone selector after selecting command', async () => {
    const user = userEvent.setup()
    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    await waitFor(() => {
      expect(screen.getByLabelText(/Writing Tone/)).toBeInTheDocument()
    })
  })

  it('shows generate button with command name', async () => {
    const user = userEvent.setup()
    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate Executive Summary/ })).toBeInTheDocument()
    })
  })

  it('calls API to generate content when clicking generate', async () => {
    const user = userEvent.setup()

    vi.mocked(api.post).mockResolvedValue({
      command: 'executive-summary',
      section_name: 'Executive Summary',
      content: 'Generated executive summary content...',
      word_count: 150,
      confidence_score: 0.85,
      generation_method: 'llm',
      rfp_id: 'RFP-2024-001',
      suggestions: [],
    })

    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate Executive Summary/ })).toBeInTheDocument()
    })

    const generateButton = screen.getByRole('button', { name: /Generate Executive Summary/ })
    await user.click(generateButton)

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/generation/RFP-2024-001/writer',
        expect.objectContaining({
          command: 'executive-summary',
          tone: 'professional',
        })
      )
    })
  })

  it('displays generated content after successful generation', async () => {
    const user = userEvent.setup()

    vi.mocked(api.post).mockResolvedValue({
      command: 'executive-summary',
      section_name: 'Executive Summary',
      content: 'This is the generated executive summary content.',
      word_count: 150,
      confidence_score: 0.85,
      generation_method: 'llm',
      rfp_id: 'RFP-2024-001',
      suggestions: ['Add more metrics'],
    })

    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate Executive Summary/ })).toBeInTheDocument()
    })

    const generateButton = screen.getByRole('button', { name: /Generate Executive Summary/ })
    await user.click(generateButton)

    await waitFor(() => {
      expect(screen.getByText('This is the generated executive summary content.')).toBeInTheDocument()
    })
  })

  it('shows word count and confidence after generation', async () => {
    const user = userEvent.setup()

    vi.mocked(api.post).mockResolvedValue({
      command: 'executive-summary',
      section_name: 'Executive Summary',
      content: 'Generated content.',
      word_count: 150,
      confidence_score: 0.85,
      generation_method: 'llm',
      rfp_id: 'RFP-2024-001',
      suggestions: [],
    })

    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    const generateButton = screen.getByRole('button', { name: /Generate Executive Summary/ })
    await user.click(generateButton)

    await waitFor(() => {
      expect(screen.getByText('150 words')).toBeInTheDocument()
      expect(screen.getByText('85% confident')).toBeInTheDocument()
    })
  })

  it('shows quick improve buttons after generation', async () => {
    const user = userEvent.setup()

    vi.mocked(api.post).mockResolvedValue({
      command: 'executive-summary',
      section_name: 'Executive Summary',
      content: 'Generated content.',
      word_count: 150,
      confidence_score: 0.85,
      generation_method: 'llm',
      rfp_id: 'RFP-2024-001',
      suggestions: [],
    })

    render(<AIWriterMenu {...defaultProps} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    const generateButton = screen.getByRole('button', { name: /Generate Executive Summary/ })
    await user.click(generateButton)

    await waitFor(() => {
      expect(screen.getByText('More Persuasive')).toBeInTheDocument()
      expect(screen.getByText('Add Metrics')).toBeInTheDocument()
      expect(screen.getByText('Add Compliance')).toBeInTheDocument()
      expect(screen.getByText('More Concise')).toBeInTheDocument()
    })
  })

  it('calls onContentGenerated callback when content is generated', async () => {
    const user = userEvent.setup()
    const onContentGenerated = vi.fn()

    vi.mocked(api.post).mockResolvedValue({
      command: 'executive-summary',
      section_name: 'Executive Summary',
      content: 'Generated content.',
      word_count: 150,
      confidence_score: 0.85,
      generation_method: 'llm',
      rfp_id: 'RFP-2024-001',
      suggestions: [],
    })

    render(<AIWriterMenu {...defaultProps} onContentGenerated={onContentGenerated} />)

    const button = screen.getByRole('combobox')
    await user.click(button)

    await waitFor(() => {
      expect(screen.getByText('/exec')).toBeInTheDocument()
    })

    const execCommand = screen.getByText('/exec')
    await user.click(execCommand)

    const generateButton = screen.getByRole('button', { name: /Generate Executive Summary/ })
    await user.click(generateButton)

    await waitFor(() => {
      expect(onContentGenerated).toHaveBeenCalledWith('Generated content.', 'Executive Summary')
    })
  })
})
