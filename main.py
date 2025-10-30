from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StudyWithAI API")

# CORS configuration to match the headers in the error
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    context: Optional[str] = Field(None, max_length=10000)
    
    @validator('question')
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()


class AskResponse(BaseModel):
    answer: str
    confidence: Optional[float] = None
    sources: Optional[list] = None


@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Handle POST requests to /api/ask endpoint.
    
    This endpoint processes questions and returns AI-generated answers.
    """
    try:
        logger.info(f"Received question: {request.question[:100]}...")
        
        # Validate the request data
        if not request.question:
            raise HTTPException(
                status_code=400,
                detail="Question is required"
            )
        
        # TODO: Integrate with actual AI model
        # For now, return a placeholder response
        answer = f"This is a placeholder response for: {request.question}"
        
        response = AskResponse(
            answer=answer,
            confidence=0.85,
            sources=[]
        )
        
        logger.info("Successfully processed question")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal server error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request"
        )


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "message": "StudyWithAI API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
