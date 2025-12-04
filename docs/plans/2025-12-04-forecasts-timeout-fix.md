# Forecasts Page Timeout Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Forecasts/Future Opportunities page timeout issue by implementing a "load on demand" pattern with persistent file-based caching that survives container restarts.

**Architecture:** Replace auto-generate-on-page-load with a two-phase approach: (1) immediately show cached predictions from a JSON file if available, (2) provide a "Generate Predictions" button for manual refresh. This eliminates timeouts on page load while still allowing fresh predictions when needed.

**Tech Stack:** FastAPI, React Query, file-based JSON caching (no Redis dependency)

---

## Analysis Summary

**Current Problem:**
- Page auto-triggers prediction generation on every load (line 356-384 in FutureOpportunities.tsx)
- Generation can take 25-55 seconds, causing 504 Gateway Timeout errors
- Redis caching exists but Redis is disabled in docker-compose.yml
- In-memory cache is lost on container restart

**Solution Chosen:** Option 4 - "Generate Predictions" button with file-based persistent cache
- Best UX: instant page load with cached data
- No Redis dependency
- Cache survives container restarts
- User controls when to regenerate

---

### Task 1: Add File-Based Cache to Backend

**Files:**
- Modify: `api/app/routes/predictions.py:28-37`

**Step 1: Add file cache constants and helper functions**

Add after line 37 (after Redis cache keys):

```python
# File-based cache (persists across container restarts)
CACHE_FILE = PathConfig.DATA_DIR / "cache" / "predictions_cache.json"

def get_cached_predictions_from_file() -> tuple[list[dict] | None, dict | None]:
    """Get cached predictions from file."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('predictions'), data.get('meta')
    except Exception as e:
        logger.warning(f"File cache read failed: {e}")
    return None, None

def cache_predictions_to_file(predictions: list[dict], meta: dict):
    """Cache predictions to file."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump({'predictions': predictions, 'meta': meta}, f)
        logger.info(f"Cached {len(predictions)} predictions to file")
    except Exception as e:
        logger.warning(f"File cache write failed: {e}")
```

**Step 2: Verify the edit compiles**

Run: `docker-compose logs --tail=5 backend`
Expected: No import errors, uvicorn running

**Step 3: Commit**

```bash
git add api/app/routes/predictions.py
git commit -m "feat(predictions): add file-based cache helpers"
```

---

### Task 2: Update Cache Write to Include File Cache

**Files:**
- Modify: `api/app/routes/predictions.py:188-200`

**Step 1: Update the cache section in generate_predictions_with_timeout**

Find this block (around line 188-200):
```python
        # Update cache
        _cached_predictions = predictions
        _cache_timestamp = time.time()

        meta = {
            "count": len(predictions),
            "ai_enhanced_count": ai_enhanced_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - start_time, 2),
        }

        # Cache to Redis
        cache_predictions_to_redis(predictions, meta)
```

Replace with:
```python
        # Update in-memory cache
        _cached_predictions = predictions
        _cache_timestamp = time.time()

        meta = {
            "count": len(predictions),
            "ai_enhanced_count": ai_enhanced_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - start_time, 2),
        }

        # Cache to file (persistent) and Redis (if available)
        cache_predictions_to_file(predictions, meta)
        cache_predictions_to_redis(predictions, meta)
```

**Step 2: Verify backend reloads without errors**

Run: `docker-compose logs --tail=5 backend`
Expected: No errors, uvicorn running

**Step 3: Commit**

```bash
git add api/app/routes/predictions.py
git commit -m "feat(predictions): write cache to file for persistence"
```

---

### Task 3: Update Cache Read Priority (File > Redis)

**Files:**
- Modify: `api/app/routes/predictions.py:255-263`

**Step 1: Update the Redis cache check section to check file first**

Find this block (around line 255-263):
```python
    # Check Redis cache
    if not refresh:
        redis_predictions, redis_meta = get_cached_predictions_from_redis()
        if redis_predictions:
            _cached_predictions = redis_predictions
            _cache_timestamp = time.time()
            filtered = [p for p in redis_predictions if p["confidence"] >= confidence]
            logger.info(f"Returning {len(filtered)} Redis-cached predictions")
            return filtered
```

Replace with:
```python
    # Check file cache first (most reliable), then Redis
    if not refresh:
        # Try file cache first (persists across restarts)
        file_predictions, file_meta = get_cached_predictions_from_file()
        if file_predictions:
            _cached_predictions = file_predictions
            _cache_timestamp = time.time()
            filtered = [p for p in file_predictions if p["confidence"] >= confidence]
            logger.info(f"Returning {len(filtered)} file-cached predictions")
            return filtered

        # Fallback to Redis cache
        redis_predictions, redis_meta = get_cached_predictions_from_redis()
        if redis_predictions:
            _cached_predictions = redis_predictions
            _cache_timestamp = time.time()
            filtered = [p for p in redis_predictions if p["confidence"] >= confidence]
            logger.info(f"Returning {len(filtered)} Redis-cached predictions")
            return filtered
```

**Step 2: Verify backend reloads**

Run: `docker-compose logs --tail=5 backend`
Expected: No errors

**Step 3: Commit**

```bash
git add api/app/routes/predictions.py
git commit -m "feat(predictions): prioritize file cache over Redis"
```

---

### Task 4: Update Fallback Endpoint to Check File Cache

**Files:**
- Modify: `api/app/routes/predictions.py:420-430`

**Step 1: Add file cache check to fallback endpoint**

Find this block (around line 420-430):
```python
    # Check Redis
    redis_predictions, redis_meta = get_cached_predictions_from_redis()
    if redis_predictions:
        filtered = [p for p in redis_predictions if p["confidence"] >= confidence]
        return {
            "status": "redis_cached",
            "predictions": filtered,
            "count": len(filtered),
            "generated_at": redis_meta.get("generated_at") if redis_meta else None,
        }
```

Replace with:
```python
    # Check file cache
    file_predictions, file_meta = get_cached_predictions_from_file()
    if file_predictions:
        filtered = [p for p in file_predictions if p["confidence"] >= confidence]
        return {
            "status": "file_cached",
            "predictions": filtered,
            "count": len(filtered),
            "generated_at": file_meta.get("generated_at") if file_meta else None,
        }

    # Check Redis
    redis_predictions, redis_meta = get_cached_predictions_from_redis()
    if redis_predictions:
        filtered = [p for p in redis_predictions if p["confidence"] >= confidence]
        return {
            "status": "redis_cached",
            "predictions": filtered,
            "count": len(filtered),
            "generated_at": redis_meta.get("generated_at") if redis_meta else None,
        }
```

**Step 2: Verify backend reloads**

Run: `docker-compose logs --tail=5 backend`
Expected: No errors

**Step 3: Commit**

```bash
git add api/app/routes/predictions.py
git commit -m "feat(predictions): add file cache to fallback endpoint"
```

---

### Task 5: Update Cache Clear to Include File Cache

**Files:**
- Modify: `api/app/routes/predictions.py:382-399`

**Step 1: Update clear_predictions_cache to also clear file**

Find the clear_predictions_cache function (around line 382-399):
```python
@router.delete("/cache")
async def clear_predictions_cache():
    """Clear the predictions cache to force a refresh."""
    global _cached_predictions, _cache_timestamp

    _cached_predictions = None
    _cache_timestamp = 0

    # Clear Redis cache too
    client = get_redis_client()
    if client:
        try:
            client.delete(REDIS_PREDICTIONS_KEY)
            client.delete(REDIS_PREDICTIONS_META_KEY)
        except Exception:
            pass

    return {"status": "cache_cleared"}
```

Replace with:
```python
@router.delete("/cache")
async def clear_predictions_cache():
    """Clear all prediction caches to force a refresh."""
    global _cached_predictions, _cache_timestamp

    _cached_predictions = None
    _cache_timestamp = 0

    # Clear file cache
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
            logger.info("File cache cleared")
    except Exception as e:
        logger.warning(f"Failed to clear file cache: {e}")

    # Clear Redis cache too
    client = get_redis_client()
    if client:
        try:
            client.delete(REDIS_PREDICTIONS_KEY)
            client.delete(REDIS_PREDICTIONS_META_KEY)
        except Exception:
            pass

    return {"status": "cache_cleared"}
```

**Step 2: Verify backend reloads**

Run: `docker-compose logs --tail=5 backend`
Expected: No errors

**Step 3: Commit**

```bash
git add api/app/routes/predictions.py
git commit -m "feat(predictions): clear file cache in delete endpoint"
```

---

### Task 6: Add getPredictionStatus API Method

**Files:**
- Modify: `frontend/src/services/api.ts:320-322`

**Step 1: Add getPredictionStatus method**

Find around line 320-322:
```typescript
  getPredictionStatus: () =>
    apiClient.get('/predictions/status').then(res => res.data),
```

If it doesn't exist, add it after getPredictions (around line 318):
```typescript
  getPredictionStatus: () =>
    apiClient.get('/predictions/status').then(res => res.data),
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors related to api.ts

**Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): add getPredictionStatus method"
```

---

### Task 7: Refactor FutureOpportunities to Load-on-Demand Pattern

**Files:**
- Modify: `frontend/src/pages/FutureOpportunities.tsx`

**Step 1: Replace auto-fetch query with status check + manual trigger**

Replace the main query block (lines 346-384):
```typescript
  // Main predictions query with 60s timeout
  const {
    data: predictions,
    isLoading,
    error,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['predictions'],
    queryFn: async () => {
      setLoadingPhase('checking_cache')
      setLoadingProgress(10)

      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setLoadingProgress((prev) => {
          if (prev < 30) return prev + 5
          if (prev < 60) return prev + 3
          if (prev < 85) return prev + 2
          return prev
        })
        setElapsedSeconds((prev) => prev + 1)
      }, 1000)

      try {
        setLoadingPhase('loading_data')
        const result = await api.getPredictions(0.3, { timeout: 55, use_ai: true })
        setLoadingPhase('complete')
        setLoadingProgress(100)
        return result
      } finally {
        clearInterval(progressInterval)
      }
    },
    retry: 1,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  })
```

With this new implementation:
```typescript
  // Check for cached predictions on page load (fast, no generation)
  const {
    data: cachedData,
    isLoading: isLoadingCache,
    refetch: refetchCache,
  } = useQuery({
    queryKey: ['predictions-cache'],
    queryFn: () => api.getFallbackPredictions(0.3),
    staleTime: 60 * 1000, // 1 minute
  })

  // Manual generation state
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationError, setGenerationError] = useState<string | null>(null)

  // Use cached predictions if available
  const predictions = cachedData?.predictions || fallbackPredictions
  const hasCachedData = predictions && predictions.length > 0
  const cacheStatus = cachedData?.status || 'no_data'

  // Manual generation function
  const handleGeneratePredictions = async () => {
    setIsGenerating(true)
    setGenerationError(null)
    setLoadingPhase('checking_cache')
    setLoadingProgress(10)
    setElapsedSeconds(0)

    const progressInterval = setInterval(() => {
      setLoadingProgress((prev) => {
        if (prev < 30) return prev + 5
        if (prev < 60) return prev + 3
        if (prev < 85) return prev + 2
        return prev
      })
      setElapsedSeconds((prev) => prev + 1)
    }, 1000)

    try {
      setLoadingPhase('loading_data')
      await api.clearPredictionCache()
      const result = await api.getPredictions(0.3, { timeout: 55, use_ai: true })
      setLoadingPhase('complete')
      setLoadingProgress(100)
      // Refetch cache to update UI
      await refetchCache()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      setGenerationError(errorMessage)
      setLoadingPhase('error')
    } finally {
      clearInterval(progressInterval)
      setIsGenerating(false)
    }
  }

  // Derive loading/error states from new pattern
  const isLoading = isLoadingCache
  const isFetching = isGenerating
  const isError = !!generationError && !hasCachedData
  const error = generationError ? new Error(generationError) : null
```

**Step 2: Update the refresh button handler**

Find the handleRefresh function (around line 410-414):
```typescript
  const handleRefresh = async () => {
    setFallbackPredictions(null)
    await api.clearPredictionCache().catch(() => {})
    refetch()
  }
```

Replace with:
```typescript
  const handleRefresh = async () => {
    setFallbackPredictions(null)
    await handleGeneratePredictions()
  }
```

**Step 3: Remove the useEffect that auto-fetches on error**

Find and remove this block (lines 387-399):
```typescript
  // Fetch fallback predictions on error
  useEffect(() => {
    if (isError && !fallbackPredictions) {
      api.getFallbackPredictions(0.3)
        .then((result) => {
          if (result.predictions && result.predictions.length > 0) {
            setFallbackPredictions(result.predictions)
          }
        })
        .catch(() => {
          // Ignore fallback errors
        })
    }
  }, [isError, fallbackPredictions])
```

**Step 4: Verify TypeScript compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/pages/FutureOpportunities.tsx
git commit -m "refactor(forecasts): load cached predictions on page load, manual generation"
```

---

### Task 8: Add "Generate Predictions" Button to Empty State

**Files:**
- Modify: `frontend/src/pages/FutureOpportunities.tsx`

**Step 1: Update the empty/no-cache state to show generate button**

Find the section that handles when there's no data (around line 541-575). After the stats summary section (around line 541), add a conditional for when there's no cached data:

Add this before `<PredictionGrid predictions={predictions || []} />`:

```typescript
      {/* Show generate button when no cached data */}
      {!hasCachedData && !isGenerating && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <BarChart3 className="mx-auto h-12 w-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
              No Predictions Available
            </h3>
            <p className="text-slate-500 max-w-md mx-auto mb-6">
              Generate AI-powered predictions based on historical government contract data.
              This process may take 30-60 seconds.
            </p>
            <Button onClick={handleGeneratePredictions} size="lg">
              <Sparkles className="h-4 w-4 mr-2" />
              Generate Predictions
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Show loading state when generating */}
      {isGenerating && (
        <LoadingState
          phase={loadingPhase}
          progress={loadingProgress}
          elapsedSeconds={elapsedSeconds}
        />
      )}

      {/* Show generation error if any */}
      {generationError && hasCachedData && (
        <Card className="border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">Generation failed: {generationError}. Showing cached data.</span>
            </div>
          </CardContent>
        </Card>
      )}
```

**Step 2: Update the header button section to show "Generate" when no data**

Find the header button section (around line 517-537). Update the button:

```typescript
          <Button
            variant={hasCachedData ? "outline" : "default"}
            size="sm"
            onClick={handleRefresh}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : hasCachedData ? (
              <RefreshCw className="h-4 w-4 mr-2" />
            ) : (
              <Sparkles className="h-4 w-4 mr-2" />
            )}
            {isGenerating ? 'Generating...' : hasCachedData ? 'Refresh Analysis' : 'Generate Predictions'}
          </Button>
```

**Step 3: Verify it compiles and renders**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/pages/FutureOpportunities.tsx
git commit -m "feat(forecasts): add Generate Predictions button for empty state"
```

---

### Task 9: Update Loading State Handling

**Files:**
- Modify: `frontend/src/pages/FutureOpportunities.tsx`

**Step 1: Update the loading state check**

Find the loading state section (around line 416-446):
```typescript
  // Loading state
  if (isLoading) {
```

Replace with:
```typescript
  // Initial cache loading (fast)
  if (isLoadingCache) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="h-6 w-6 text-blue-500" />
              Future Opportunities
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1">
              AI-powered forecasting of recurring government contracts
            </p>
          </div>
        </div>

        {/* Brief loading skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <PredictionSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }
```

**Step 2: Remove the old loading return that shows full loading state on initial load**

The old loading block showed the full LoadingState component on initial load. Now we only show that during manual generation. Remove/update as needed based on Step 1.

**Step 3: Verify it compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/pages/FutureOpportunities.tsx
git commit -m "refactor(forecasts): show brief skeleton for cache check, full loading for generation"
```

---

### Task 10: Test the Complete Flow

**Step 1: Clear any existing cache**

```bash
rm -f /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/data/cache/predictions_cache.json
```

**Step 2: Restart backend to pick up changes**

```bash
docker-compose restart backend
```

**Step 3: Test the page loads instantly without timeout**

Open http://localhost/forecasts in browser.
Expected: Page loads immediately showing "No Predictions Available" with Generate button

**Step 4: Test generation works**

Click "Generate Predictions" button.
Expected: Loading state shows progress, completes in 30-60 seconds, predictions appear

**Step 5: Test cache persistence**

```bash
docker-compose restart backend
```

Open http://localhost/forecasts again.
Expected: Page loads instantly with previously generated predictions

**Step 6: Commit final changes**

```bash
git add -A
git commit -m "feat(forecasts): complete timeout fix with persistent cache and manual generation"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `api/app/routes/predictions.py` | Added file-based cache (read/write/clear) |
| `frontend/src/services/api.ts` | Added getPredictionStatus method |
| `frontend/src/pages/FutureOpportunities.tsx` | Changed to load-on-demand pattern with Generate button |

## Benefits

1. **No more timeouts on page load** - Page loads instantly with cached data or empty state
2. **Persistent cache** - Survives container restarts (file-based)
3. **User control** - Users decide when to regenerate predictions
4. **Clear feedback** - Loading progress shown during generation
5. **No Redis dependency** - Works without Redis enabled
