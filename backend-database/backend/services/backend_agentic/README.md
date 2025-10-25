# Agentic Backend

A production-capable backend system that processes natural language queries through a multi-agent orchestration framework. Combines web scraping, vector search, structured data retrieval, and LLM processing to provide evidence-backed answers.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agentic-backend
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

4. **Install Playwright browsers**
   ```bash
   playwright install
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Ingest sample data**
   ```bash
   python scripts/ingest_sample_data.py
   ```

### Running the Application

1. **Start the API server**
   ```bash
   uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 📁 Project Structure

```
agentic-backend/
├── services/
│   ├── api_gateway/          # FastAPI application
│   │   ├── main.py          # Main API entry point
│   │   └── routes/          # API route definitions
│   └── orchestrator/        # Orchestration logic
│       ├── orchestrator.py  # Main orchestrator
│       └── router_client.py # Query routing
├── workers/                 # Worker entry points
│   ├── scraper_worker.py    # Web scraping worker
│   ├── embedder_worker.py   # Embedding worker
│   └── fact_retriever_worker.py # CSV data worker
├── tools/                   # MCP tool implementations
│   ├── scraper.py          # Web scraping tool
│   ├── embedder.py         # Embedding tool
│   └── vector_query.py     # Vector search tool
├── aggregator/             # Result processing
│   ├── aggregator.py       # Result aggregation
│   └── prompt_builder.py   # LLM prompt construction
├── llm/                    # LLM integration
│   ├── deepseek_client.py  # DeepSeek API client
│   └── verifier.py         # Response verification
├── scripts/                # Utility scripts
│   └── ingest_sample_data.py # Sample data ingestion
├── docs/                   # Documentation
│   └── architecture.md     # System architecture
├── tests/                  # Test files
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── data/                   # Data files
│   └── facts.csv          # Sample lead data
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# DeepSeek Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Vector Database (Optional)
VECTOR_DB_URL=your_vector_db_url_here
PINECONE_API_KEY=your_pinecone_api_key_here

# Development Settings
ENABLE_MOCK_RESPONSES=true
DEBUG_MODE=true
```

### Development vs Production

- **Development**: Uses mock responses and in-memory storage
- **Production**: Requires real API keys and persistent storage

## 📡 API Usage

### Main Query Endpoint

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "query": "Compare lead_2 and lead_3 and tell which has better growth potential",
    "options": {
      "mode": "sync",
      "timeout_seconds": 10
    }
  }'
```

### Tool Test Endpoints

#### Test Web Scraping
```bash
curl -X POST "http://localhost:8000/tool/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/financials",
    "selectors": ["/financials", "/news"]
  }'
```

#### Test Facts CSV Query
```bash
curl -X POST "http://localhost:8000/tool/facts_csv_query" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "lead_2",
    "fields": ["revenue_2023", "employees"]
  }'
```

#### Test Vector Query
```bash
curl -X POST "http://localhost:8000/tool/query_vectors" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "revenue growth financial data",
    "top_k": 5
  }'
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=agentic-backend
```

### Manual Testing with Postman

1. Import the Postman collection from `docs/postman_collection.json`
2. Set the base URL to `http://localhost:8000`
3. Run the test scenarios

## 🔄 Development Workflow

### Adding New Tools

1. Create tool implementation in `tools/`
2. Add worker entry point in `workers/`
3. Update orchestrator to handle new tool
4. Add test endpoints in API gateway
5. Write tests

### Adding New Query Types

1. Update router logic in `router_client.py`
2. Add prompt template in `prompt_builder.py`
3. Update aggregator if needed
4. Add tests

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .

# Run all quality checks
make quality
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build image
docker build -t agentic-backend .

# Run container
docker run -p 8000:8000 agentic-backend
```

### Production Considerations

1. **Environment Variables**: Set all required API keys
2. **Database**: Configure persistent storage
3. **Monitoring**: Enable logging and metrics
4. **Security**: Implement authentication and rate limiting
5. **Scaling**: Use load balancer and multiple instances

## 📊 Monitoring

### Logs

The application uses structured logging. Log levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General information about application flow
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failed operations

### Metrics

Key metrics to monitor:
- Query processing time
- Tool execution success rates
- LLM response quality scores
- API endpoint response times

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use type hints
- Handle errors gracefully

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](http://localhost:8000/docs)
- [Migration Guide](docs/migration.md)

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **API Key Errors**: Check environment variables
3. **Playwright Issues**: Run `playwright install`
4. **Port Conflicts**: Change port in uvicorn command

### Getting Help

- Check the logs for error messages
- Review the API documentation
- Open an issue on GitHub

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI for the web framework
- DeepSeek for LLM capabilities
- Pinecone for vector database
- Playwright for web scraping 