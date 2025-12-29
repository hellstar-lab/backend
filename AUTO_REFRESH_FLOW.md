# Weather Auto-Refresh Flow Specification

This document defines the exact sequence of events for real-time weather updates, ensuring synchronization between the frontend polling mechanism and backend caching.

## 🔄 Sequence Diagram

### 1. Initial Load (Time 0:00)
- **User Action**: Opens dashboard, enters "London".
- **Frontend**: Calls `GET /api/weather/current/London`.
- **Backend**:
  1. Checks Firestore cache -> **MISS**.
  2. Calls Open-Meteo API.
  3. Transforms data.
  4. Stores in Firestore cache (TTL: 5 mins).
  5. Returns data (Status: 200 OK).
- **Frontend**: Displays weather, stores `lastRefresh` timestamp.

### 2. First Poll Interval (Time 5:00)
- **Trigger**: Frontend timer (5 min elapsed).
- **Frontend**: Calls `GET /api/weather/poll/London` with header `If-Modified-Since: <lastRefresh>`.
- **Backend**:
  1. Checks Firestore cache -> **HIT**.
  2. Compares cache timestamp with header.
  3. Data is not newer -> Returns **304 Not Modified**.
- **Frontend**: Receives 304, keeps existing data displayed.

### 3. Force Refresh / Stale Data (Time 10:00)
- **Trigger**: Timer triggers again (or user clicks "Refresh").
- **Frontend**: Calls `GET /api/weather/current/London?force=true` (or standard poll if cache expired).
- **Backend**:
  1. Checks Firestore cache -> **EXPIRED** (or bypassed via force flag).
  2. Calls Open-Meteo API.
  3. Updates Firestore cache with new data.
  4. Returns fresh data (Status: 200 OK).
- **Frontend**: Updates UI with new data, shows "Updated just now" toast.

## 🛠 Implementation Details

### Frontend (React)
```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/weather/poll/${city}`, {
      headers: {
        'If-Modified-Since': lastRefresh.toISOString()
      }
    });
    
    if (response.status === 200) {
      const newData = await response.json();
      setWeatherData(newData);
      setLastRefresh(new Date());
      showToast("Weather updated");
    }
    // If 304, do nothing
  }, 300000); // 5 minutes

  return () => clearInterval(interval);
}, [city, lastRefresh]);
```

### Backend (FastAPI)
- **Endpoint**: `GET /api/weather/poll/{city}`
- **Logic**:
  - Validates city.
  - Checks cache.
  - Returns `304` if `cache_timestamp <= If-Modified-Since`.
  - Returns `200` + data if new data available.
  - Fetches fresh data if cache missing.
