from typing import List, Literal, Optional
from pydantic import BaseModel, Field, validator
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm
from app.graph.state import ProjectState
import json

class ClassificationOutput(BaseModel):
    user_level: Literal["beginner", "intermediate", "advanced"] = Field(description="The coding proficiency level of the user")
    project_type: Literal["web_app", "component", "full_stack"] = Field(description="The type of project requested")
    complexity: Literal["simple", "medium", "complex"] = Field(description="The complexity of the request")
    requires_research: bool = Field(description="Whether the request requires external research")
    tech_stack: List[str] = Field(description="List of technologies to use (e.g. react, tailwind)")
    extracted_requirements: List[str] = Field(description="List of specific requirements extracted from the prompt")
    
    # CRITICAL FIX: Pydantic v1 validators to handle type coercion
    @validator('requires_research', pre=True)
    def coerce_boolean(cls, v):
        """Convert string booleans to actual booleans"""
        if isinstance(v, str):
            return v.lower().strip() in ('true', '1', 'yes', 't')
        return bool(v) if v is not None else False
    
    @validator('tech_stack', 'extracted_requirements', pre=True)
    def ensure_list(cls, v):
        """Ensure lists are actually lists"""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        if isinstance(v, list):
            return v
        try:
            return list(v)
        except:
            return []

async def classifier_agent(state: ProjectState):
    """
    Analyzes the user prompt and classifies the request.
    """
    prompt = state["original_prompt"]
    
    llm = get_llm(temperature=0)
    # Use json_schema to avoid Groq function/tool calling behavior for structured output
    structured_llm = llm.with_structured_output(ClassificationOutput, method="json_schema")
    
    # Updated system prompt with explicit type instructions and mobile-first enforcement
    system_prompt = """You are a software project analyst. Classify the user's request accurately.

    USER LEVEL:
    - beginner: vague request, no technical terms, no library mentions
    - intermediate: mentions specific libraries, routing, state management
    - advanced: mentions architecture patterns, auth, real-time, APIs, optimization

    PROJECT TYPE:
    - component: single UI element or widget
    - web_app: single-page app, no backend
    - full_stack: requires backend, database, or auth

    COMPLEXITY:
    - simple: single page, static content, no logic
    - medium: multiple views, state, basic data fetching
    - complex: auth, real-time, external APIs, complex business logic

    requires_research (boolean): true only if domain-specific UI/UX inspiration is needed
    (e.g. barbershop, hospital dashboard, crypto tracker — NOT generic todo apps)

    tech_stack: always include ["react", "tailwind", "vite"] as base. Add extras if specified.
    extracted_requirements: concrete features only. Always append "mobile-first responsive design"."""
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{prompt}")
    ])
    
    chain = prompt_template | structured_llm
    
    try:
        result: ClassificationOutput = await chain.ainvoke({"prompt": prompt})
        
        print(f"✅ Classification successful:")
        print(f"   - User Level: {result.user_level}")
        print(f"   - Project Type: {result.project_type}")
        print(f"   - Complexity: {result.complexity}")
        print(f"   - Requires Research: {result.requires_research} (type: {type(result.requires_research).__name__})")
        print(f"   - Tech Stack: {result.tech_stack}")
        
        return {"classification": result.dict()}
    
    except Exception as e:
        print(f"❌ Classification error: {e}")
        print(f"   Using fallback classification")
        
        # Fallback classification
        return {
            "classification": {
                "user_level": "beginner",
                "project_type": "web_app",
                "complexity": "medium",
                "requires_research": False,  # Boolean!
                "tech_stack": ["react", "tailwind"],
                "extracted_requirements": [prompt[:100]]
            }
        }