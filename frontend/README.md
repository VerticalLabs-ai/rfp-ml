# RFP Bid Generation Dashboard

A modern, robust frontend UI for the RFP (Request for Proposal) Bid Generation System built with React, TypeScript, Vite, Tailwind CSS, and shadcn/ui.

## Tech Stack

- **Framework**: React 18.3 with TypeScript 5.7
- **Build Tool**: Vite 6.0 (fast, modern development experience)
- **Styling**: Tailwind CSS 4.1 with shadcn/ui components
- **State Management**:
  - Zustand (global state)
  - TanStack Query (React Query 5.62) for server state
- **Routing**: React Router DOM 6.28
- **Icons**: Lucide React
- **Charts**: Recharts 2.15
- **Notifications**: Sonner (shadcn/ui toast)
- **Real-time**: WebSocket support with auto-reconnection

## Features

### ✨ Core Features

- **Dashboard**: Comprehensive overview with real-time statistics
  - Total RFPs discovered, in pipeline, pending review, and submitted
  - Submission performance metrics
  - Recent RFP opportunities with status badges

- **RFP Discovery**: Browse and triage discovered opportunities
  - Advanced filtering (search, stage, sort)
  - Inline triage actions (Approve, Review, Reject)
  - Real-time score display

- **Pipeline Monitor**: Track RFP progress through stages
- **Decision Review**: Review and approve/reject bid opportunities
- **Submission Queue**: Monitor bid submission status

### 🎨 Design System

- **shadcn/ui Components**: High-quality, accessible UI components
  - Button, Card, Table, Dialog, Badge, Input, Label, Select
  - Sidebar, Skeleton, Sheet, Tooltip, Separator
- **Dark Mode**: Full dark mode support (system-based)
- **Responsive**: Mobile-first design with responsive breakpoints
- **Animations**: Smooth transitions and loading states

### 🔌 Real-time Features

- **WebSocket Integration**:
  - Live connection status indicator
  - Auto-reconnection with exponential backoff
  - Real-time pipeline updates
  - Toast notifications for connection events

### 🎯 Developer Experience

- **TypeScript**: Full type safety across the codebase
- **Path Aliases**: `@/` imports for cleaner code organization
- **ESLint**: Code quality and consistency
- **Hot Module Replacement**: Instant feedback during development

## Project Structure

```text
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── ui/          # shadcn/ui components
│   │   ├── Layout.tsx   # Main layout with navigation
│   │   ├── DashboardLayout.tsx
│   │   ├── StatsCard.tsx
│   │   ├── RFPCard.tsx
│   │   ├── FilterBar.tsx
│   │   ├── RecentRFPs.tsx
│   │   └── WebSocketStatus.tsx
│   ├── pages/           # Page components
│   │   ├── Dashboard.tsx
│   │   ├── RFPDiscovery.tsx
│   │   ├── PipelineMonitor.tsx
│   │   ├── DecisionReview.tsx
│   │   └── SubmissionQueue.tsx
│   ├── hooks/           # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   └── use-mobile.ts
│   ├── services/        # API integration
│   │   └── api.ts       # Axios client + WebSocket
│   ├── types/           # TypeScript types
│   │   └── rfp.ts
│   ├── utils/           # Utility functions
│   ├── lib/             # Library utilities
│   │   └── utils.ts     # cn() helper
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles + Tailwind
├── components.json      # shadcn/ui configuration
├── tsconfig.json        # TypeScript configuration
├── vite.config.ts       # Vite configuration
├── tailwind.config.js   # Tailwind CSS configuration
└── package.json         # Dependencies and scripts
```

## Getting Started

### Prerequisites

- Node.js 18+ or 20+
- npm or yarn or pnpm

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

The development server will start at [http://localhost:3000](http://localhost:3000)

### Environment Setup

The frontend is configured to proxy API requests to the FastAPI backend:

- **API Base URL**: `http://localhost:8000/api/v1` (proxied via Vite)
- **WebSocket URL**: `ws://localhost:8000/ws/pipeline`

Make sure the FastAPI backend is running on port 8000 before starting the frontend.

## API Integration

### REST API

The frontend integrates with the following FastAPI endpoints:

```typescript
// RFP endpoints
GET    /api/v1/rfps/discovered       # Get discovered RFPs (with filters)
GET    /api/v1/rfps/:id              # Get single RFP
POST   /api/v1/rfps/:id/triage       # Update triage decision
GET    /api/v1/rfps/stats/overview   # Get RFP statistics
GET    /api/v1/rfps/recent           # Get recent RFPs

// Pipeline endpoints
GET    /api/v1/pipeline/status       # Get pipeline status
GET    /api/v1/pipeline/:id          # Get RFP pipeline details

// Decision endpoints
GET    /api/v1/rfps/discovered?stage=decision_pending
POST   /api/v1/rfps/:id/advance-stage
PUT    /api/v1/rfps/:id              # Update RFP

// Submission endpoints
GET    /api/v1/submissions/queue     # Get submission queue
GET    /api/v1/submissions/:id       # Get submission details
POST   /api/v1/submissions           # Create submission
POST   /api/v1/submissions/:id/retry # Retry submission
GET    /api/v1/submissions/stats/overview
```

### WebSocket

Real-time updates via WebSocket at `ws://localhost:8000/ws/pipeline`:

```typescript
// Message format
{
  type: 'rfp_update' | 'pipeline_update' | 'submission_update',
  data: any,
  timestamp: string
}
```

## Component Usage

### Using shadcn/ui Components

```tsx
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

function Example() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Example Card</CardTitle>
      </CardHeader>
      <CardContent>
        <Badge variant="secondary">Status</Badge>
        <Button size="sm">Click Me</Button>
      </CardContent>
    </Card>
  )
}
```

### Using WebSocket Hook

```tsx
import { useWebSocket } from '@/hooks/useWebSocket'

function Component() {
  const { isConnected, lastMessage, sendMessage } = useWebSocket({
    url: 'ws://localhost:8000/ws/pipeline',
    onMessage: (message) => {
      console.log('Received:', message)
    }
  })

  return <div>Connected: {isConnected ? 'Yes' : 'No'}</div>
}
```

## Adding New shadcn/ui Components

To add more shadcn/ui components:

```bash
npx shadcn@latest add [component-name]

# Examples:
npx shadcn@latest add dropdown-menu
npx shadcn@latest add tabs
npx shadcn@latest add form
npx shadcn@latest add calendar
```

## Customization

### Theme Colors

Edit `src/index.css` to customize the color palette:

```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    /* ... more CSS variables */
  }
}
```

### Tailwind Configuration

Edit `tailwind.config.js` to customize Tailwind settings:

```js
module.exports = {
  theme: {
    extend: {
      // Your custom theme extensions
    }
  }
}
```

## Performance Optimizations

- **Code Splitting**: Automatic route-based code splitting with React Router
- **Tree Shaking**: Vite automatically removes unused code
- **Asset Optimization**: Images and fonts optimized during build
- **React Query**: Smart caching and background refetching
- **WebSocket**: Efficient real-time updates without polling

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Troubleshooting

### Port Already in Use

If port 3000 is already in use, change it in `vite.config.ts`:

```typescript
server: {
  port: 3001, // Change to desired port
  proxy: { /* ... */ }
}
```

### TypeScript Errors

If you see path alias errors, ensure `tsconfig.json` includes:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### WebSocket Connection Fails

Ensure the FastAPI backend is running and WebSocket endpoint is available at `ws://localhost:8000/ws/pipeline`.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run `npm run lint` to check code quality
4. Test your changes thoroughly
5. Submit a pull request

## License

[Add your license here]

## Support

For issues or questions, please contact the development team or create an issue in the repository.
