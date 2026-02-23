from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from typing import List, Dict
from app.services.llm import get_llm
from app.graph.state import ProjectState

class FileBlueprint(BaseModel):
    filename: str = Field(description="Path and name of the file (e.g. src/components/Header.jsx)")
    description: str = Field(description="Description of what this file contains")
    imports: List[str] = Field(description="Expected imports")

class DesignSpec(BaseModel):
    architecture_overview: str = Field(description="High level explanation of the architecture")
    styling_guide: str = Field(description="Tailwind color palette and design tokens to use")
    component_hierarchy: str = Field(description="Tree structure of components")
    file_structure: List[FileBlueprint] = Field(description="List of files to generate")

async def design_agent(state: ProjectState):
    """
    Plans the architecture and file structure.
    """
    classification = state.get("classification")
    research = state.get("research_context", {})
    prompt = state["original_prompt"]
    
    llm = get_llm(temperature=0.2)
    # Use json_schema method to avoid Groq function/tool calling behavior
    structured_llm = llm.with_structured_output(DesignSpec, method="json_schema")
    
    system_prompt = """You are a Senior React Architect. Design a complete file structure for a mobile-first React + Tailwind + Vite app.

    LAYOUT RULES:
    - Mobile-first: design for 320-428px, scale up with md: and lg: breakpoints
    - Navigation: bottom nav or hamburger for mobile; sidebar/topnav for desktop
    - Tap targets: minimum 44px height on all interactive elements
    - Containers: "container mx-auto px-4" with "max-w-7xl" cap

    FILE STRUCTURE RULES:
    - src/components/ for reusable UI
    - src/pages/ for route-level views (if routing needed)
    - Required config files: package.json, vite.config.js, tailwind.config.js, postcss.config.js, index.html
    - index.html MUST include viewport meta tag

    For each file provide: filename, a clear description of its purpose, and expected imports.
    The file list you produce is the exact list the Code Generator will build — be complete and deliberate."""
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Request: {prompt}\nResearch: {research}\nClassification: {classification}")
    ])
    
    chain = prompt_template | structured_llm
    
    result = await chain.ainvoke({
        "prompt": prompt,
        "research": research.get("summary", "None"),
        "classification": classification
    })
    
    return {"design_spec": result.dict()}
