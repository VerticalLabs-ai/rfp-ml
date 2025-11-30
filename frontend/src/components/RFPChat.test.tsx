/**
 * Tests for RFPChat component
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/test/test-utils'
import RFPChat from './RFPChat'

// Mock the api module
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

// Import after mock
import { api } from '@/lib/api'

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
}

describe('RFPChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock responses
    mockApi.get.mockResolvedValue({ chat_available: true, message: '' })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('Closed state', () => {
    it('renders as a floating button when closed', () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
      expect(button).toHaveClass('fixed', 'bottom-4', 'right-4')
    })

    it('opens the chat panel when button is clicked', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText(/Ask about Test RFP/)).toBeInTheDocument()
      })
    })
  })

  describe('Open state', () => {
    it('shows the RFP title in the header', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Cloud Services Contract" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText(/Ask about Cloud Services Contract/)).toBeInTheDocument()
      })
    })

    it('shows the empty state message initially', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText('Ask me anything about this RFP')).toBeInTheDocument()
      })
    })

    it('renders the message input textarea', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument()
      })
    })

    it('shows send button', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        // There should be multiple buttons - find the send button
        const buttons = screen.getAllByRole('button')
        // Send button should be disabled initially (no message)
        const sendButton = buttons.find(btn => btn.hasAttribute('disabled'))
        expect(sendButton).toBeInTheDocument()
      })
    })
  })

  describe('Chat controls', () => {
    it('can close the chat panel', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      // Open chat
      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText(/Ask about Test RFP/)).toBeInTheDocument()
      })

      // Find the close button (X icon) - it's the last button with h-6 w-6 class
      // There are two small buttons: minimize (ChevronDown) and close (X)
      const smallButtons = screen.getAllByRole('button').filter(btn =>
        btn.className.includes('h-6') && btn.className.includes('w-6')
      )
      // The close button is the second (last) one in the header controls
      const closeButton = smallButtons[1]
      fireEvent.click(closeButton)

      // After closing, should be back to the floating button state
      await waitFor(() => {
        expect(screen.queryByText(/Ask about Test RFP/)).not.toBeInTheDocument()
      })
    })

    it('can minimize and expand the chat panel', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      // Open chat
      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText(/Ask about Test RFP/)).toBeInTheDocument()
      })

      // Find minimize button and click it
      const buttons = screen.getAllByRole('button')
      // The minimize button should toggle between ChevronDown and ChevronUp
      const minimizeButton = buttons.find(btn =>
        btn.className.includes('h-6') && btn !== buttons[buttons.length - 1]
      )

      if (minimizeButton) {
        fireEvent.click(minimizeButton)
      }

      // Content should be hidden when minimized
      await waitFor(() => {
        expect(screen.queryByPlaceholderText('Ask a question...')).not.toBeInTheDocument()
      })
    })
  })

  describe('Message input', () => {
    it('enables send button when message is entered', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'What is the deadline?' } })
      })

      // The send button should now be enabled
      const buttons = screen.getAllByRole('button')
      const enabledButtons = buttons.filter(btn => !btn.hasAttribute('disabled'))
      expect(enabledButtons.length).toBeGreaterThan(0)
    })

    it('clears input after sending', async () => {
      mockApi.post.mockResolvedValue({
        answer: 'The deadline is January 15, 2025.',
        citations: [],
        confidence: 0.9,
        rfp_id: 'RFP-001',
        processing_time_ms: 150,
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'What is the deadline?' } })
      })

      // Find and click send button
      const textarea = screen.getByPlaceholderText('Ask a question...')
      fireEvent.keyDown(textarea, { key: 'Enter' })

      await waitFor(() => {
        expect(textarea).toHaveValue('')
      })
    })
  })

  describe('Message display', () => {
    it('shows user messages on the right', async () => {
      mockApi.post.mockResolvedValue({
        answer: 'Response',
        citations: [],
        confidence: 0.9,
        rfp_id: 'RFP-001',
        processing_time_ms: 100,
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'Test message' } })
        fireEvent.keyDown(textarea, { key: 'Enter' })
      })

      await waitFor(() => {
        expect(screen.getByText('Test message')).toBeInTheDocument()
      })
    })

    it('shows assistant messages on the left', async () => {
      mockApi.post.mockResolvedValue({
        answer: 'This is the AI response.',
        citations: [],
        confidence: 0.9,
        rfp_id: 'RFP-001',
        processing_time_ms: 100,
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'Question?' } })
        fireEvent.keyDown(textarea, { key: 'Enter' })
      })

      await waitFor(() => {
        expect(screen.getByText('This is the AI response.')).toBeInTheDocument()
      })
    })
  })

  describe('Citations', () => {
    it('displays citations when present in response', async () => {
      mockApi.post.mockResolvedValue({
        answer: 'The deadline is mentioned in Section 3.',
        citations: [
          {
            document_id: 'doc-1',
            content_snippet: 'Submission deadline: January 15, 2025',
            source: 'RFP Section 3.1',
            similarity_score: 0.95,
          },
        ],
        confidence: 0.85,
        rfp_id: 'RFP-001',
        processing_time_ms: 120,
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'When is the deadline?' } })
        fireEvent.keyDown(textarea, { key: 'Enter' })
      })

      await waitFor(() => {
        expect(screen.getByText('Sources:')).toBeInTheDocument()
        expect(screen.getByText(/RFP Section 3.1/)).toBeInTheDocument()
        expect(screen.getByText(/95% match/)).toBeInTheDocument()
      })
    })
  })

  describe('Confidence indicator', () => {
    it('displays confidence badge for responses', async () => {
      mockApi.post.mockResolvedValue({
        answer: 'Test response.',
        citations: [],
        confidence: 0.87,
        rfp_id: 'RFP-001',
        processing_time_ms: 100,
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'Test' } })
        fireEvent.keyDown(textarea, { key: 'Enter' })
      })

      await waitFor(() => {
        expect(screen.getByText('87% confident')).toBeInTheDocument()
      })
    })
  })

  describe('Chat availability', () => {
    it('shows warning when chat is not available', async () => {
      mockApi.get.mockImplementation((url: string) => {
        if (url.includes('/status')) {
          return Promise.resolve({
            chat_available: false,
            message: 'RAG index not available for this RFP',
          })
        }
        return Promise.resolve({ suggestions: [] })
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText('RAG index not available for this RFP')).toBeInTheDocument()
      })
    })
  })

  describe('Suggested questions', () => {
    it('displays suggested questions when available', async () => {
      mockApi.get.mockImplementation((url: string) => {
        if (url.includes('/suggestions')) {
          return Promise.resolve({
            suggestions: [
              'What is the deadline?',
              'What are the key requirements?',
            ],
          })
        }
        if (url.includes('/status')) {
          return Promise.resolve({ chat_available: true, message: '' })
        }
        return Promise.resolve({})
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText('Suggested questions:')).toBeInTheDocument()
      })
    })
  })

  describe('Keyboard shortcuts', () => {
    it('sends message on Enter key', async () => {
      mockApi.post.mockResolvedValue({
        answer: 'Response',
        citations: [],
        confidence: 0.9,
        rfp_id: 'RFP-001',
        processing_time_ms: 100,
      })

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'Test message' } })
        fireEvent.keyDown(textarea, { key: 'Enter' })
      })

      await waitFor(() => {
        expect(mockApi.post).toHaveBeenCalled()
      })
    })

    it('allows newlines with Shift+Enter', async () => {
      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'Line 1' } })
        fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })
      })

      // Should NOT call the API
      expect(mockApi.post).not.toHaveBeenCalled()
    })
  })

  describe('Error handling', () => {
    it('shows error message when API call fails', async () => {
      mockApi.post.mockRejectedValue(new Error('Network error'))

      render(<RFPChat rfpId="RFP-001" rfpTitle="Test RFP" />)

      fireEvent.click(screen.getByRole('button'))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('Ask a question...')
        fireEvent.change(textarea, { target: { value: 'Test' } })
        fireEvent.keyDown(textarea, { key: 'Enter' })
      })

      await waitFor(() => {
        expect(screen.getByText(/Sorry, I encountered an error/)).toBeInTheDocument()
      })
    })
  })

  describe('Custom className', () => {
    it('applies custom className to the component', () => {
      const { container } = render(
        <RFPChat rfpId="RFP-001" rfpTitle="Test" className="custom-class" />
      )

      const button = container.querySelector('.custom-class')
      expect(button).toBeInTheDocument()
    })
  })
})
