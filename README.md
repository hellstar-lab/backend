# Vornics Weather AI - Backend

Production-ready Python backend for the Vornics Weather AI Platform. Built with FastAPI, Firebase, and Open-Meteo.

## 🚀 Features

- **Real-Time Weather**: Current weather, 7-day forecasts, and hourly updates via Open-Meteo API.
- **AI Chatbot**: Intelligent weather assistant powered by OpenAI GPT-4.
- **Smart Alerts**: Customizable weather alerts with real-time monitoring.
- **User Management**: Firebase Authentication integration and user profiles.
- **Performance**: Multi-layer caching (Firestore + In-Memory) and rate limiting.
- **Real-Time Updates**: Server-Sent Events (SSE) for live data streaming.

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: Firebase Firestore
- **Authentication**: Firebase Auth
- **External APIs**: Open-Meteo, OpenAI GPT-4
- **Deployment**: Render / Google Cloud Run

## 📂 Project Structure

```
backend/
├── api/                 # API Routes
│   ├── auth_routes.py   # Authentication
│   ├── weather_routes.py# Weather endpoints
│   ├── alerts_routes.py # Alert management
│   ├── chatbot_routes.py# AI Chatbot
│   └── sse_routes.py    # Real-time streaming
├── services/            # Business Logic
│   ├── weather_service.py
│   ├── chatbot_service.py
│   ├── alert_service.py
│   └── cache_service.py
├── models/              # Pydantic Models
├── utils/               # Helper Functions
├── middleware/          # CORS, Error Handling
├── config.py            # Configuration
└── app.py               # Main Entry Point
```

## ⚡ Getting Started

### Prerequisites

- Python 3.11+
- Firebase Project (with Firestore & Auth enabled)
- OpenAI API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

5. **Run Locally**
   ```bash
   uvicorn app:app --reload
   ```
   Access API documentation at `http://localhost:8000/docs`

## 🧪 Testing

Run the test suite:
```bash
pytest
```

## 📦 Deployment

Ready for deployment on Render, Heroku, or Google Cloud Run.
Includes `Procfile` and `render.yaml` configurations.

## 🔒 Security

- **Authentication**: Bearer token verification via Firebase Admin SDK.
- **Validation**: Strict input validation using Pydantic models.
- **CORS**: Configured for specific frontend origins.
- **Rate Limiting**: API usage limits per user/IP.

## 📄 License

MIT License
