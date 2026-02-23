from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm
from app.core.config import get_settings
from app.graph.state import ProjectState
import json

settings = get_settings()

async def research_agent(state: ProjectState):
    """
    Performs research on the requested topic.
    """
    classification = state.get("classification", {})
    prompt = state["original_prompt"]
    
    # If no research required, skip? The graph will handle routing, but if we are here, we do research.
    
    llm = get_llm(temperature=0.2)
    
    # Mock search or use Tavily if available (Implementation of actual search omitted for brevity/dependency reasons, focusing on LLM knowledge)
    # framework for search:
    search_context = ""
    if settings.TAVILY_API_KEY:
        # TODO: Implement actual Tavily call
        pass
        
    system_prompt = """You are a product researcher. Analyze the user's request and return structured insights.

    Return exactly this structure:
    - features: 5-8 must-have features for this type of app (be specific, e.g. "Booking calendar with time slots" not "Booking")
    - ui_patterns: 3-5 UI/UX conventions for this domain (layout, navigation style, color mood)
    - color_palette: suggest 3 Tailwind color classes that fit the domain (e.g. "slate", "emerald", "amber")  
    - data_structures: 2-4 key data entities and their core fields
    - inspiration: 1-2 sentence description of the visual feel to aim for

    Be specific to the domain. Generic advice is not useful."""
    
    user_prompt = f"""
    User Request: {prompt}
    Project Type: {classification.get('project_type')}
    Context: {classification.get('extracted_requirements')}
    """
    
    messages = [
        ("system", system_prompt),
        ("human", user_prompt)
    ]
    
    response = await llm.ainvoke(messages)
    
    return {"research_context": {"summary": response.content}}
