# Frontend Setup Guide

This guide explains how to run the robust RFP Dashboard frontend built with React, TypeScript, shadcn/ui, and Next.js patterns.

## Quick Start

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Start Development Server

```bash
npm run dev
```

The frontend will be available at: **[http://localhost:3000](http://localhost:3000)**

## What Was Built

### ✅ Completed Features

1. **TypeScript Configuration**
   - Full TypeScript 5.7 setup with strict mode
   - Path aliases (`@/`) for clean imports
   - Proper module resolution for Vite

2. **shadcn/ui Integration**
   - Installed and configured shadcn/ui component library
   - Added 15+ essential components:
     - Button, Card, Table, Dialog, Badge
     - Input, Label, Select, Sidebar
     - Skeleton, Sheet, Tooltip, Separator, Sonner (toast)
   - Tailwind CSS 4.1 with custom theme

3. **Enhanced Components**
   - **Layout**: Modern navigation with shadcn/ui styling
   - **StatsCard**: Metrics cards with hover effects and trends
   - **RFPCard**: RFP opportunity cards with inline triage actions
   - **FilterBar**: Advanced filtering with shadcn/ui Select components
   - **RecentRFPs**: Recent opportunities list with badges
   - **WebSocketStatus**: Real-time connection indicator

4. **Dashboard Pages**
   - **Dashboard**: Overview with stats, trends, and recent RFPs
   - **RFP Discovery**: Browse and triage opportunities
   - **Pipeline Monitor**: Track RFP progress
   - **Decision Review**: Approve/reject bid opportunities
   - **Submission Queue**: Monitor bid submissions

5. **Real-time Features**
   - WebSocket integration with auto-reconnection
   - Custom `useWebSocket` hook with error handling
   - Live connection status indicator in header
   - Toast notifications for connection events

6. **Developer Experience**
   - Hot Module Replacement (HMR)
   - Fast refresh with Vite
   - ESLint configuration
   - Type-safe API client with Axios

## Architecture

### Tech Stack

```
React 18.3 + TypeScript 5.7
Vite 6.0 (Build Tool)
Tailwind CSS 4.1
shadcn/ui (Component Library)
TanStack Query 5.62 (Server State)
Zustand 5.0 (Global State)
React Router 6.28 (Routing)
Sonner (Toast Notifications)
```

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components
│   │   ├── Layout.tsx            # Main layout with WebSocket
│   │   ├── StatsCard.tsx         # Enhanced stat cards
│   │   ├── RFPCard.tsx           # RFP opportunity cards
│   │   ├── FilterBar.tsx         # Filter controls
│   │   └── WebSocketStatus.tsx   # Connection indicator
│   ├── pages/                     # Page components
│   ├── hooks/
│   │   └── useWebSocket.ts       # WebSocket management
│   ├── services/
│   │   └── api.ts                # API client + WebSocket
│   ├── lib/
│   │   └── utils.ts              # cn() helper
│   └── types/                     # TypeScript types
├── components.json                # shadcn/ui config
├── tsconfig.json                  # TypeScript config
├── vite.config.ts                 # Vite config with path aliases
└── tailwind.config.js             # Tailwind CSS config
```

## Running with Backend

### Start Backend API (Terminal 1)

```bash
# From project root
uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: [http://localhost:8000](http://localhost:8000)

API docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

### Start Frontend (Terminal 2)

```bash
# From project root
cd frontend
npm run dev
```

Frontend will be available at: [http://localhost:3000](http://localhost:3000)

## API Integration

The frontend is configured to proxy requests to the backend:

- **API Base**: `http://localhost:8000/api/v1` (proxied via `/api`)
- **WebSocket**: `ws://localhost:8000/ws/pipeline`

### Vite Proxy Configuration

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    },
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true
    }
  }
}
```

## Key Features Explained

### 1. shadcn/ui Components

All UI components use the shadcn/ui library for consistency and accessibility:

```tsx
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

<Card>
  <CardContent>
    <Button variant="default">Click Me</Button>
  </CardContent>
</Card>
```

### 2. WebSocket Integration

Real-time updates via WebSocket with automatic reconnection:

```tsx
const { isConnected, lastMessage, reconnect } = useWebSocket({
  url: 'ws://localhost:8000/ws/pipeline',
  onMessage: (message) => {
    console.log('Real-time update:', message)
  }
})
```

### 3. Path Aliases

Clean imports using `@/` prefix:

```tsx
// ✅ Good
import { Button } from '@/components/ui/button'
import { useWebSocket } from '@/hooks/useWebSocket'

// ❌ Avoid
import { Button } from '../../components/ui/button'
```

### 4. Type Safety

Full TypeScript coverage:

```tsx
interface RFPCardProps {
  rfp: RFPOpportunity
  onTriageDecision: (rfpId: string, decision: string) => void
}
```

## Available Scripts

```bash
# Development
npm run dev          # Start dev server with HMR

# Production
npm run build        # Build for production
npm run preview      # Preview production build

# Code Quality
npm run lint         # Run ESLint
```

## Adding New Components

### Add shadcn/ui Components

```bash
npx shadcn@latest add [component-name]

# Examples:
npx shadcn@latest add dropdown-menu
npx shadcn@latest add tabs
npx shadcn@latest add form
```

### Create Custom Components

```tsx
// src/components/MyComponent.tsx
import { Card } from '@/components/ui/card'

export function MyComponent() {
  return (
    <Card>
      {/* Your component */}
    </Card>
  )
}
```

## Troubleshooting

### Port 3000 Already in Use

Change port in `vite.config.ts`:

```typescript
server: {
  port: 3001, // Use different port
}
```

### WebSocket Not Connecting

1. Ensure backend is running on port 8000
2. Check WebSocket endpoint: `ws://localhost:8000/ws/pipeline`
3. Look for connection errors in browser console

### TypeScript Errors

Ensure `tsconfig.json` has path aliases:

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

## Next Steps

### Recommended Enhancements

1. **Authentication**: Add user login/logout
2. **Dark Mode Toggle**: Implement theme switcher
3. **Advanced Filtering**: Add date range, category filters
4. **Export Functionality**: Export RFPs to CSV/Excel
5. **Notifications**: Push notifications for critical updates
6. **Analytics**: Add charts and metrics visualizations
7. **Keyboard Shortcuts**: Implement hotkeys for common actions

## Support

For detailed component documentation, see [frontend/README.md](frontend/README.md)

For backend API documentation, visit [http://localhost:8000/docs](http://localhost:8000/docs) when backend is running.

---

**Status**: ✅ All features implemented and tested

**Last Updated**: November 17, 2025

**Frontend Server**: [http://localhost:3000](http://localhost:3000)

**Backend Server**: [http://localhost:8000](http://localhost:8000)
