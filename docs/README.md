# 🤖 Multi-Agent Orchestration System

A sophisticated multi-agent orchestration system built with FastAPI, LangGraph, and React. This system enables intelligent coordination between multiple AI agents to accomplish complex tasks through structured workflows.

## 🎯 Overview

The Multi-Agent Orchestration System provides:
- **Intelligent Agent Coordination**: Multiple specialized agents working together
- **Real-time Workflow Visualization**: Live updates of agent execution and dependencies
- **Dynamic Task Planning**: Automatic task breakdown and dependency resolution
- **Customizable Agent Behaviors**: Configurable prompts, priorities, and execution parameters
- **Session Management**: Persistent orchestration sessions with history and export capabilities

## 🏗️ Architecture

### Backend (Python/FastAPI)
- **FastAPI**: High-performance API framework
- **LangGraph**: Stateful workflow orchestration
- **PostgreSQL**: Session and task persistence
- **Qdrant**: Vector database for RAG operations
- **Redis**: Caching and session management
- **WebSocket**: Real-time communication

### Frontend (React/Next.js)
- **Next.js**: Modern React framework
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Beautiful icons
- **WebSocket Client**: Real-time updates

### Agent Types
1. **Research Agent**: Document analysis and RAG operations
2. **MCP Agent**: External tool execution via MCP protocol
3. **Data Agent**: Data processing and analysis
4. **Reviewer Agent**: Result synthesis and review
5. **Code Agent**: Code generation and analysis
6. **Image Agent**: Image processing and analysis
7. **Summary Agent**: Content summarization

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- OpenAI API key (optional for full functionality)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/multi-agent-orchestrator.git
cd multi-agent-orchestrator
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start with Docker Compose**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Development Setup

1. **Backend setup**
```bash
cd app
pip install -r requirements.txt
uvicorn main:app --reload
```

2. **Frontend setup**
```bash
cd frontend
npm install
npm run dev
```

## 📚 API Documentation

### Core Endpoints

#### Orchestration
- `POST /orchestrate` - Start new orchestration session
- `GET /orchestrate/{session_id}` - Get session details
- `POST /orchestrate/{session_id}/pause` - Pause session
- `POST /orchestrate/{session_id}/resume` - Resume session
- `GET /orchestrate` - List all sessions
- `DELETE /orchestrate/{session_id}` - Delete session

#### Agents
- `GET /agents` - List available agents
- `GET /agents/{agent_type}` - Get agent details

#### WebSocket
- `ws://localhost:8000/ws/orchestrate/{session_id}` - Real-time session updates

### Example Usage

```python
import requests

# Start a new orchestration session
response = requests.post("http://localhost:8000/orchestrate", json={
    "goal": "Analyze Q3 sales data and generate comprehensive report",
    "selected_agents": ["research", "data", "reviewer"]
})

session = response.json()
print(f"Session started: {session['session_id']}")
```

```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket(`ws://localhost:8000/ws/orchestrate/${sessionId}`);

ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('Session update:', update);
};
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM operations | Required |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:password@localhost/rag_ai` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `QDRANT_URL` | Qdrant vector database URL | `http://localhost:6333` |
| `NEXT_PUBLIC_API_URL` | Frontend API URL | `http://localhost:8000` |

### Agent Customization

Each agent can be customized through the UI or API:

```json
{
  "agent_type": "research",
  "name": "Custom Research Agent",
  "enabled": true,
  "priority": 1,
  "custom_prompt": "You are a specialized research assistant...",
  "max_retries": 3,
  "timeout": 60
}
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_orchestrator.py

# Run with coverage
pytest --cov=app tests/

# Run async tests
pytest -m asyncio
```

### Test Structure

- `tests/test_orchestrator.py` - Core orchestration tests
- `tests/test_agents.py` - Individual agent tests
- `tests/test_api.py` - API endpoint tests
- `tests/test_integration.py` - Full workflow tests

## 📦 Deployment

### Production Deployment

1. **Configure production environment**
```bash
cp .env.example .env.production
# Edit with production values
```

2. **Deploy with production Docker Compose**
```bash
./scripts/deploy.sh
```

3. **Monitor deployment**
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Environment-Specific Configurations

- **Development**: `docker-compose.yml`
- **Production**: `docker-compose.prod.yml`
- **Testing**: `docker-compose.test.yml`

## 🔍 Monitoring & Logging

### Health Checks
- Backend: `GET /health`
- Frontend: Automatic health checks
- Database: Connection monitoring
- Redis: Ping monitoring

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log aggregation ready (ELK stack compatible)

### Metrics
- Request/response times
- Agent execution metrics
- Session success rates
- Resource utilization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Write comprehensive tests
- Update documentation
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Documentation](https://docs.multi-agent-orchestrator.com)
- 🐛 [Issue Tracker](https://github.com/your-org/multi-agent-orchestrator/issues)
- 💬 [Discussions](https://github.com/your-org/multi-agent-orchestrator/discussions)
- 📧 [Email Support](mailto:support@multi-agent-orchestrator.com)

## 🎉 Features

### ✅ Implemented
- [x] Multi-agent orchestration with LangGraph
- [x] Real-time workflow visualization
- [x] Agent customization and configuration
- [x] Session management and history
- [x] WebSocket real-time updates
- [x] Specialized agents (Code, Image, Summary)
- [x] Production deployment setup
- [x] Comprehensive testing suite
- [x] API documentation

### 🚧 In Progress
- [ ] Advanced monitoring and alerting
- [ ] CI/CD pipeline integration
- [ ] Performance optimization
- [ ] Additional agent types
- [ ] Multi-tenant support

### 📋 Planned
- [ ] Machine learning-based task optimization
- [ ] Advanced error handling and recovery
- [ ] Plugin system for custom agents
- [ ] Mobile application
- [ ] Enterprise SSO integration

## 🏆 Acknowledgments

- [LangChain](https://langchain.com/) - LLM orchestration framework
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Next.js](https://nextjs.org/) - React production framework
- [Qdrant](https://qdrant.tech/) - Vector database
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework

---

**Built with ❤️ by the Multi-Agent Orchestration Team**
