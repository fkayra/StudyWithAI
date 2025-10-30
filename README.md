# StudyWithAI

An AI-powered study assistant API that helps answer questions.

## Features

- FastAPI-based REST API
- Question answering endpoint with proper validation
- CORS support for web applications
- Comprehensive error handling
- Request validation using Pydantic

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Start the server:

```bash
python main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 3000
```

## API Endpoints

### POST /api/ask

Submit a question to get an AI-generated answer.

**Request Body:**
```json
{
  "question": "What is Python?",
  "context": "optional context"
}
```

**Response:**
```json
{
  "answer": "Answer to your question",
  "confidence": 0.85,
  "sources": []
}
```

**Status Codes:**
- 200: Success
- 400: Bad request (invalid input)
- 422: Validation error
- 500: Internal server error

### GET /

Health check endpoint.

### GET /health

Detailed health status.

## Error Handling

The API includes comprehensive error handling:
- Input validation errors return 422 with detailed error messages
- Server errors return 500 with generic error messages (sensitive information is logged but not exposed)
- All errors are logged for debugging

## Development

The API is built with:
- FastAPI for the web framework
- Uvicorn as the ASGI server
- Pydantic for data validation
