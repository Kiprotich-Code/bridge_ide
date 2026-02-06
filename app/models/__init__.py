from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class CodeExecutionRequest(BaseModel):
    """Request model for code execution"""
    code: str
    language: Optional[str] = None
    filename: Optional[str] = None
    stdin: Optional[str] = None


class CodeExecutionResult(BaseModel):
    """Result model for code execution"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    time: Optional[float] = None
    memory: Optional[int] = None
    token: Optional[str] = None
    status: Optional[dict] = None


class GithubAuthRequest(BaseModel):
    """GitHub OAuth callback code"""
    code: str


class GithubUser(BaseModel):
    """GitHub user model"""
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    user: Optional[GithubUser] = None
    token: Optional[str] = None
    error: Optional[str] = None


class GenerateRequest(BaseModel):
    """Request to generate a new project from prompt"""
    prompt: str
    user_id: Union[str, int]  # Accept both string and integer
    
    @field_validator('user_id', mode='before')
    @classmethod
    def convert_user_id(cls, v):
        return str(v)  # Always convert to string


class RefineRequest(BaseModel):
    """Request to refine an existing project"""
    project_id: str
    feedback: str
    user_id: Union[str, int]  # Accept both string and integer
    
    @field_validator('user_id', mode='before')
    @classmethod
    def convert_user_id(cls, v):
        return str(v)  # Always convert to string


class ExecuteRequest(BaseModel):
    """Request to execute a project"""
    project_id: str
    files: Optional[Dict[str, str]] = None


class ConversationMessage(BaseModel):
    """Single message in conversation history"""
    role: str  # "user" or "assistant"
    content: str


class ProjectState(BaseModel):
    """Complete state of a project"""
    project_id: Optional[str] = None
    user_id: Union[str, int]  # Accept both string and integer
    original_prompt: str
    iteration_count: int = 0
    conversation_history: List[ConversationMessage] = []
    current_files: Dict[str, str] = {}
    user_feedback: Optional[str] = None
    status: str = "generating"  # "generating", "completed", "error"
    
    @field_validator('user_id', mode='before')
    @classmethod
    def convert_user_id(cls, v):
        return str(v)  # Always convert to string


class SSEInitEvent(BaseModel):
    """SSE init event data"""
    project_id: str


class SSEProgressEvent(BaseModel):
    """SSE progress event data"""
    node: str
    message: str


class SSEFilesEvent(BaseModel):
    """SSE files event data"""
    files: Dict[str, str]


class SSECompleteEvent(BaseModel):
    """SSE complete event data"""
    project_id: str
    files: Dict[str, str]
