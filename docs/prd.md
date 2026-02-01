# Facility Intelligence System

AI-powered facility monitoring dashboard with natural language interaction.

## Overview

The Facility Intelligence System transforms passive sensor monitoring into proactive facility intelligence. Users interact with an interactive floor plan blueprint showing all sensors, and chat with an AI assistant that can query data, explain anomalies, and generate visualizations.

## Features

### Interactive Blueprint

- Floor plan view displaying 4 zones: Loading Bay, Cold Room A (Fresh), Cold Room B (Frozen), Dry Storage
- 11 sensors with real-time status indicators (normal/warning/critical)
- Clickable sensor markers showing detailed readings, sparkline trends, and statistics
- Draggable sensor positioning for layout customization

### AI Assistant

- Natural language chat with streaming responses
- Tool-augmented responses using LangGraph ReAct pattern
- Context-aware facility operations expertise
- Markdown-formatted responses with action links

### Data Query Tools

- **query_sensor_data**: Historical readings with hourly/daily aggregation
- **get_door_events**: Door open/close timeline with duration calculations
- **get_thermal_presence**: Motion events with freezer safety concern flags (>10 min exposure)
- **get_baselines**: Statistical baselines for anomaly context

### Visualization Generation

- AI-generated visualization ideas based on conversation context
- Dynamic chart generation using Recharts components
- Two-step generation: data gathering + JSX code synthesis
- Live rendering via react-live

## Tech Stack

### Frontend
- React 18 + TypeScript 5 (strict mode)
- Vite 7 build tooling
- Tailwind CSS 4 styling
- TanStack Query for data fetching
- Recharts for visualizations
- react-live for dynamic chart rendering

### Backend
- Python 3.11+ with FastAPI
- SQLAlchemy 2 (async) + aiosqlite
- LangGraph for agent orchestration
- Anthropic Claude for LLM (Sonnet for chat, Opus for code generation)

### Database
- SQLite with 4 zones, 11 sensors
- Reading tables: Environmental, AirQuality, Door, Motion
- 48 hours of generated realistic data with patterns

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/sensors` | All sensors with current readings and trends |
| `GET /api/sensors/{id}/readings` | Historical readings with time range |
| `GET /api/sensors/{id}/baseline` | Statistical baseline |
| `GET /api/doors/events` | Door events with durations |
| `GET /api/presence/events` | Motion events with safety flags |
| `POST /api/agent/chat` | SSE streaming chat |
| `POST /api/agent/ideas` | Generate visualization ideas |
| `POST /api/agent/visualize` | Generate visualization code |

## Facility Layout

| Zone | Type | Target Temp | Sensors |
|------|------|-------------|---------|
| Loading Bay | Ambient | 15-25°C | temp, door, air quality, motion |
| Cold Room A | Fresh | 2-4°C | temp, motion |
| Cold Room B | Frozen | -20 to -16°C | temp, door, motion |
| Dry Storage | Ambient | 15-20°C | temp, air quality |

## Running Locally

```bash
# Backend
cd backend
python scripts/setup_database.py  # First time only
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173
