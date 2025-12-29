# Testing & Validation Protocol

This document defines the comprehensive testing strategy for the Vornics Weather AI backend, covering unit tests, integration flows, and security validation.

## 🧪 Step 9.1: Unit Test Requirements

### Weather Service Tests (`tests/test_weather_service.py`)

#### `test_transform_current_weather`
- **Input**: Sample Open-Meteo JSON response (current + daily).
- **Expected**: `WeatherData` dictionary matching frontend schema.
- **Must Test**:
  - WMO weather code mapping (e.g., 0 -> "Clear sky").
  - Unit handling (metric vs imperial).
  - Handling of missing optional fields (e.g., visibility).
  - Date/Time formatting (ISO strings).

#### `test_geocode_city`
- **Input**: "London".
- **Expected**: `{"lat": 51.5074, "lon": -0.1278, "country": "United Kingdom", ...}`.
- **Must Test**:
  - Ambiguous city names (e.g., "London" vs "London, KY").
  - Non-existent cities (should raise 404).
  - API timeouts/errors (should raise 503).
  - Cache interaction (if mocking DB).

### Chatbot Service Tests (`tests/test_chatbot_service.py`)

#### `test_intent_recognition`
- **Input**: "What's the weather in Paris?"
- **Expected**: `Intent.WEATHER`, entity="Paris".
- **Must Test**:
  - Various phrasings ("Paris weather", "forecast for Paris").
  - Case insensitivity.
  - Non-weather queries (fallback to chat).

### Alert Service Tests (`tests/test_alert_service.py`)

#### `test_check_condition`
- **Input**: Alert(threshold=30, type='temp', op='>'), Current(temp=32).
- **Expected**: `True` (Triggered).
- **Must Test**:
  - All operators (>, <, =).
  - All data types (temp, humidity, wind).
  - Boundary conditions (temp=30).

---

## 🔗 Step 9.2: Integration Test Requirements

### `test_complete_user_journey`

**Flow:**
1. **User Signup**: Mock Firebase Auth to create a test user context.
2. **Initial Query**: Call `GET /api/weather/current/Paris`.
   - Verify `query_history` collection has new document.
   - Verify `weather_cache` has entry for Paris coordinates.
3. **Repeat Query**: Call `GET /api/weather/current/Paris` again (within 5 min).
   - Verify response time is < 100ms (Cache Hit).
   - Verify NO call made to external Open-Meteo mock.
4. **History Check**: Call `GET /api/history/queries`.
   - Verify 2 entries returned (or 1 if deduped logic applies).
   - Verify data matches initial query.
5. **Cleanup**: Delete user and verify cascade deletion of history.

---

## 🔒 Step 9.3: Firestore Security Rules Tests

These tests should be run using the Firebase Emulator Suite.

### `test_query_history_security`
```javascript
// Test: User cannot read another user's history
const db = getFirestore(authedApp({uid: 'user1'}));
const otherUserDoc = db.collection('query_history').doc('user2_query');
await assertFails(otherUserDoc.get());

// Test: User can read own history
const ownDoc = db.collection('query_history').doc('user1_query');
await assertSucceeds(ownDoc.get());
```

### `test_weather_cache_security`
```javascript
// Test: Unauthenticated user CAN read weather cache (public read)
const db = getFirestore(null); // No auth
const cacheDoc = db.collection('weather_cache').doc('london_cache');
await assertSucceeds(cacheDoc.get());

// Test: Unauthenticated user CANNOT write to cache
await assertFails(cacheDoc.set({data: 'hacked'}));
```

### `test_user_profile_security`
```javascript
// Test: User can only write to own profile
const db = getFirestore(authedApp({uid: 'user1'}));
await assertSucceeds(db.collection('users').doc('user1').set({name: 'Me'}));
await assertFails(db.collection('users').doc('user2').set({name: 'Hacker'}));
```
