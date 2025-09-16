# AI Analytics Microservice

A FastAPI-based microservice for restaurant analytics, providing sales forecasting and dynamic pricing recommendations.

## 🚀 Features

- **Sales Forecasting**: Weekly and daily sales predictions
- **Dynamic Pricing**: AI-powered pricing recommendations
- **Time Distribution Analysis**: Customer behavior patterns
- **Async Database Operations**: PostgreSQL with async SQLAlchemy
- **RESTful API**: Clean, documented endpoints

## 📁 Project Structure

```
ai-analytics-microservice/
│
├── app/
│   ├── api/
│   │   ├── routes/           # API route handlers
│   │   │   ├── weekly_forecast.py
│   │   │   ├── daily_forecast.py
│   │   │   ├── dynamic_pricing.py
│   │   │   └── time_distribution.py
│   │   └── __init__.py
│   │
│   ├── core/
│   │   ├── config.py         # App configuration & settings
│   │   └── utils.py          # Utility functions
│   │
│   ├── db/
│   │   ├── base.py           # SQLAlchemy declarative base
│   │   ├── session.py        # Database session management
│   │   └── models/           # SQLAlchemy models
│   │
│   ├── repositories/         # Data access layer
│   │   ├── menu_repository.py
│   │   ├── order_repository.py
│   │   └── forecast_repository.py
│   │
│   ├── services/             # Business logic layer
│   │   ├── forecasting_service.py
│   │   ├── dynamic_pricing_service.py
│   │   └── time_distribution_service.py
│   │
│   ├── schemas/              # Pydantic schemas
│   ├── main.py               # FastAPI application entry point
│   └── __init__.py
│
├── tests/                    # Test files
├── requirements.txt          # Python dependencies
└── README.md
```

## 🛠️ Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with asyncpg
- **ORM**: SQLAlchemy (async)
- **Configuration**: Pydantic Settings
- **Documentation**: Auto-generated OpenAPI/Swagger

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL database
- pip (Python package manager)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-analytics-microservice
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

4. **Environment Setup**
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=postgresql+asyncpg://username:password@host:port/database
   ```

## 🚀 Running the Application

### Development Mode
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

Once the application is running, you can access:

- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔌 API Endpoints

### Forecasting
- `GET /api/forecast/weekly` - Get weekly sales forecast
- `GET /api/forecast/daily` - Get daily sales forecast

### Dynamic Pricing
- `POST /api/pricing/dynamic` - Get dynamic pricing recommendations
- `GET /api/pricing/analysis` - Get pricing analysis

### Time Distribution
- `GET /api/analytics/time-distribution` - Get customer time patterns

## 🗄️ Database

The application uses PostgreSQL with async SQLAlchemy. Key components:

- **Connection**: Configured via `DATABASE_URL` environment variable
- **Session Management**: Async session factory in `app/db/session.py`
- **Models**: SQLAlchemy models in `app/db/models/`

### Testing Database Connection
```bash
python -m app.db.session
```

## 🧪 Testing

Run tests using pytest:
```bash
pytest tests/
```

## 📦 Dependencies

Key dependencies (add to `requirements.txt`):
```
fastapi
uvicorn
sqlalchemy[asyncio]
asyncpg
pydantic
pydantic-settings
```

## 🔒 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions, please open an issue in the repository. 