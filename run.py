#!/usr/bin/env python
"""
Development server runner.
Usage: python run.py
"""

if __name__ == "__main__":
    import uvicorn
    from app.core.config import get_settings
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        timeout_keep_alive=300,  # Keep connections alive for 5 minutes for long SSE streams
        timeout_graceful_shutdown=30  # Allow 30 seconds for graceful shutdown
    )
