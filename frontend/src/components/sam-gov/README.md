# SAM.gov Components

Frontend components for SAM.gov integration.

## Components

### SyncStatus

A component that displays the SAM.gov sync status and allows manual synchronization.

**Usage:**

```tsx
import { SamGovSyncStatus } from '@/components/sam-gov';

function MyPage() {
  return (
    <div>
      <SamGovSyncStatus />
    </div>
  );
}
```

**Features:**
- Real-time sync status display
- Auto-refresh every 30 seconds
- Manual sync trigger with configurable parameters
- Visual indicators for connection state
- Error message display
- Last sync timestamp (relative time)
- Opportunities synced counter

**Backend Requirements:**

The component expects the following API endpoints to be available:
- `GET /api/v1/sam-gov/status` - Get current sync status
- `POST /api/v1/sam-gov/sync` - Trigger manual sync

## API Methods

The following SAM.gov API methods are available in `@/services/api`:

### Status & Sync

- `getSamGovStatus()` - Get current sync status
- `triggerSamGovSync(params?)` - Trigger sync with optional parameters
  - `days_back?: number` - Number of days to look back
  - `limit?: number` - Maximum number of opportunities to sync

### Opportunities

- `checkSamGovUpdates(opportunityIds)` - Check for updates to specific opportunities
- `getSamGovOpportunityDetails(noticeId)` - Get full details for an opportunity
- `getSamGovAmendments(noticeId, daysBack?)` - Get amendments for an opportunity

### Entity Verification

- `verifySamGovEntity(params)` - Verify entity registration
  - `uei?: string` - Unique Entity Identifier
  - `cage_code?: string` - CAGE code
  - `legal_name?: string` - Legal business name
- `getSamGovEntityProfile(uei)` - Get full entity profile
- `syncCompanyFromSamGov(uei)` - Sync company profile from SAM.gov

## TypeScript Types

```typescript
interface SamGovStatus {
  status: 'idle' | 'syncing' | 'error';
  last_sync: string | null;
  last_error: string | null;
  opportunities_synced: number;
  is_connected: boolean;
  api_key_configured: boolean;
}

interface SamGovEntityVerification {
  is_registered: boolean;
  registration_status: string | null;
  uei: string | null;
  cage_code: string | null;
  legal_name: string | null;
  expiration_date: string | null;
  naics_codes: string[];
  error: string | null;
}
```
