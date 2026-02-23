from app.graph.state import ProjectState

# async def qa_agent(state: ProjectState):
#     """
#     Quality Assurance check.
#     """
#     # Placeholder for QA logic
#     return {}

async def qa_agent(state: ProjectState):
    files = state.get("current_files", {})
    issues = []

    # Rule-based checks (fast, no LLM needed)
    if "src/main.jsx" not in files:
        issues.append("Missing src/main.jsx")
    if "index.html" not in files:
        issues.append("Missing index.html")
    if "src/index.css" not in files:
        issues.append("Missing src/index.css — Tailwind won't load")
    
    for filename, content in files.items():
        if filename.endswith(".jsx") or filename.endswith(".js"):
            if "placeholder" in content.lower() or "todo" in content.lower():
                issues.append(f"{filename} contains placeholder content")
            if "import React" not in content and filename != "src/main.jsx":
                pass  # React 17+ doesn't need explicit import, skip
        if filename.endswith(".jsx") and "export default" not in content:
            issues.append(f"{filename} is missing a default export")

    return {
        "qa_passed": len(issues) == 0,
        "qa_issues": issues
    }