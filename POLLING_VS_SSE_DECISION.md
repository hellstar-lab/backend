# 🔄 REAL-TIME IMPLEMENTATION: POLLING VS SSE

**Date:** 2025-11-23
**Status:** ✅ Implemented (Polling)

---

## 🎯 DECISION: CLIENT-SIDE POLLING

We chose **Client-Side Polling** (Interval: 5 minutes) over Server-Sent Events (SSE) or WebSockets for the following reasons:

1.  **Data Frequency:** Weather data typically updates hourly or every 15 minutes. Real-time streaming (sub-second) is unnecessary overhead.
2.  **Simplicity:** Polling is stateless, robust, and easy to debug.
3.  **Cache Efficiency:** Our backend cache (5 min TTL) perfectly aligns with the polling interval.
4.  **Cost:** Reduces persistent connection costs on serverless platforms (like Render/Vercel).

---

## 🛠️ IMPLEMENTATION DETAILS

### 1. Backend Logic (`weather_routes.py`)
- **Endpoint:** `GET /api/weather/current/{city}`
- **Parameter:** `force=true` (optional)
- **Logic:**
  - If `force=true`: Bypass cache, fetch fresh data from Open-Meteo.
  - If `force=false`: Check Firestore cache first. If valid (TTL < 5 min), return cached data.
- **Response:**
  ```json
  {
    "source": "cache", // or "api"
    "data": { ... },   // WeatherData object
    "timestamp": 1700000000
  }
  ```

### 2. Frontend Logic (`WeatherContext.tsx`)
- **Auto-Refresh:** `setInterval` runs every 5 minutes (300,000ms).
- **Manual Refresh:** User clicks "Refresh" button -> calls API with `force=true`.
- **City Change:** Immediate fetch (default `force=false`).

---

## 🧪 VERIFICATION

### Check Polling
Open Browser Console:
```
🔄 Real-time polling activated - refreshing every 5 minutes
... (wait 5 mins) ...
🔄 Auto-refreshing weather data for New York...
```

### Check Cache
1. **First Call:** `source: "api"` (Cache MISS)
2. **Second Call (within 5 min):** `source: "cache"` (Cache HIT)
3. **Manual Refresh:** `source: "api"` (Force Refresh)
