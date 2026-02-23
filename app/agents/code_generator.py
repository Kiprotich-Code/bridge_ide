from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from typing import List, Dict
from app.services.llm import get_llm
from app.graph.state import ProjectState
import json

class CodeFile(BaseModel):
    filename: str = Field(description="The path and filename")
    content: str = Field(description="The complete code content")

class ProjectCode(BaseModel):
    files: List[CodeFile] = Field(description="List of all generated files")

async def code_generator_agent(state: ProjectState):
    """
    Generates the actual code for the project.
    """
    design_spec = state.get("design_spec")
    classification = state.get("classification")
    
    # If no design spec (simple path), we might generate on the fly, but for now assuming Design Agent ran.
    # If Design Agent didn't run (Experienced path), we simulate design or just ask for code directly.
    
    file_list = []
    if design_spec:
        # ✅ FIXED: Handle file_structure as dicts or objects
        file_structure = design_spec.get('file_structure', [])
        if file_structure and isinstance(file_structure[0], dict):
            # It's a list of dicts - use .get()
            file_list = [f.get('filename') or f.get('path') for f in file_structure]
        else:
            # It's a list of objects - use .filename
            file_list = [f.filename for f in file_structure]
        
    # Use deterministic output for structured code generation
    llm = get_llm(temperature=0.0) # Deterministic for structured JSON
    # context window management: if too many files, might need multiple calls.
    # For now, we attempt single pass for typical "demo" size apps.
    
    # Use json_schema to avoid Groq function/tool calling behavior for structured output
    structured_llm = llm.with_structured_output(ProjectCode, method="json_schema")
    
    # ✅ MOBILE-FIRST: Enhanced prompt for phone IDE
    system_prompt = """You are an Expert React Developer. Generate complete, working code for every file listed.

    STRICT RULES:
    - No placeholders, no "// TODO", no stub functions — every file must be production-ready
    - Every component uses Tailwind exclusively — no inline styles
    - Mobile-first: write base styles for mobile, add md: and lg: overrides
    - Buttons and links: always min-h-[44px] for touch targets
    - Layouts: "min-h-screen" on root, "container mx-auto px-4" for content

    REQUIRED FILE CONFIGS:
    - package.json: "type": "module", include react, react-dom, vite, @vitejs/plugin-react, tailwindcss, autoprefixer, postcss
    - vite.config.js: ESM export default defineConfig({ plugins: [react()] })
    - postcss.config.js: ESM export default { plugins: { tailwindcss: {}, autoprefixer: {} } }
    - tailwind.config.js: content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}']
    - index.html: viewport meta tag required, root div, src/main.jsx module script
    - src/index.css: @tailwind base; @tailwind components; @tailwind utilities;
    - src/main.jsx: import './index.css', render <App /> to #root

    Files to generate: {file_list}
    Design spec: {design_spec}

    Return only valid JSON matching the ProjectCode schema."""
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Design Spec: {design_spec}\n\nGenerate complete, working code for all files.")
    ])
    
    chain = prompt_template | structured_llm
    
    # ✅ Prepare input data with all required variables
    input_data = {
        "file_list": ", ".join(file_list) if file_list else "Standard React App structure",
        "design_spec": json.dumps(design_spec) if design_spec else "Create a standard robust app."
    }
    
    print(f"🔨 Generating code for {len(file_list)} files...")
    
    try:
        result = await chain.ainvoke(input_data)
        
        current_files = {f.filename: f.content for f in result.files}
        
        print(f"✅ Generated {len(current_files)} files:")
        for filename in sorted(current_files.keys()):
            print(f"   📄 {filename} ({len(current_files[filename])} bytes)")
        
        return {"current_files": current_files}
    
    except Exception as e:
        print(f"❌ Code generation error: {e}")
        print(f"   Attempting fallback generation using design_spec...")
        
        # Fallback: generate basic structure (prefer design_spec file_structure when available)
        fallback_files = generate_fallback_files(file_list, design_spec)
        print(f"   Fallback produced {len(fallback_files)} files: {sorted(list(fallback_files.keys()))[:10]}{'...' if len(fallback_files)>10 else ''}")
        return {"current_files": fallback_files}


def generate_fallback_files(file_list: List[str], design_spec: dict) -> Dict[str, str]:
    """Generate basic fallback files if LLM fails. Use design_spec.file_structure when available."""

    import os

    files = {}

    # base defaults (ensure minimal working project)
    files["package.json"] = """{
  "name": "generated-react-app",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}"""

    files["vite.config.js"] = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      onwarn(warning, warn) {
        if (warning.code === 'UNRESOLVED_IMPORT') return;
        warn(warning);
      }
    }
  }
})
"""

    files["tailwind.config.js"] = """export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
"""

    files["postcss.config.js"] = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""

    files["src/index.css"] = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""

    files["index.html"] = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Generated App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

    files["src/main.jsx"] = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

    # If design_spec provides a file_structure, use it to generate more accurate fallbacks
    components = []
    file_structure = []
    if design_spec and isinstance(design_spec, dict):
        file_structure = design_spec.get('file_structure') or design_spec.get('files') or []

    if file_structure and isinstance(file_structure, list):
        for entry in file_structure:
            # entry may be a dict (from DesignSpec) or an object with filename attribute
            if isinstance(entry, dict):
                fname = entry.get('filename') or entry.get('path')
                desc = entry.get('description', '')
            else:
                fname = getattr(entry, 'filename', None)
                desc = ''
            if not fname:
                continue
            # Normalize Windows backslashes to forward slashes
            fname = fname.replace('\\', '/').lstrip('/')

            # Components
            if fname.endswith('.jsx') or fname.endswith('.js'):
                # components under src/components
                if fname.startswith('src/components/'):
                    compname = os.path.splitext(os.path.basename(fname))[0]
                    components.append(compname)
                    files[fname] = f"""import React from 'react';

function {compname}() {{
  return (
    <div className=\"bg-gradient-to-br from-gray-800 to-gray-700 rounded-xl shadow-2xl p-4 md:p-6 lg:p-8 mb-4 md:mb-6\">\n      <h2 className=\"text-xl md:text-2xl lg:text-3xl font-bold text-orange-400 mb-3 md:mb-4\">{compname}</h2>\n      <p className=\"text-base md:text-lg text-gray-300 leading-relaxed\">{desc or f'This is the {compname} component.'}</p>\n      <button className=\"mt-4 bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 px-6 rounded-lg min-h-[44px] transition-colors duration-200\">\n        Learn More\n      </button>\n    </div>\n  );\n}}\n\nexport default {compname};\n"""
                elif fname.startswith('src/data/') or '/data/' in fname:
                    files[fname] = 'export default []'
                else:
                    # Generic JS/JSX placeholder
                    base = os.path.splitext(os.path.basename(fname))[0]
                    files[fname] = f"// Placeholder for {fname}\n\nexport default function {base}() {{\n  return null\n}}\n"

            elif fname.endswith('.html'):
                files[fname] = """<!DOCTYPE html>
<html lang=\"en\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n  <title>Generated</title>\n</head>\n<body>\n  <div id=\"root\"></div>\n  <script type=\"module\" src=\"/src/main.jsx\"></script>\n</body>\n</html>"""

            elif fname.endswith('.css'):
                files[fname] = "@tailwind base;\n@tailwind components;\n@tailwind utilities;"

            elif os.path.basename(fname) == 'package.json' or fname.endswith('package.json'):
                # Generate a valid package.json to allow npm install
                import json as _json
                pkg = {
                    "name": "generated-react-app",
                    "private": True,
                    "version": "0.0.1",
                    "type": "module",
                    "scripts": {
                        "dev": "vite",
                        "build": "vite build",
                        "preview": "vite preview"
                    },
                    "dependencies": {
                        "react": "^18.2.0",
                        "react-dom": "^18.2.0"
                    },
                    "devDependencies": {
                        "@vitejs/plugin-react": "^4.2.1",
                        "vite": "^5.0.8",
                        "tailwindcss": "^3.3.6",
                        "autoprefixer": "^10.4.16",
                        "postcss": "^8.4.32"
                    }
                }
                files[fname] = _json.dumps(pkg, indent=2)

            else:
                files[fname] = f"// Placeholder for {fname}\n"

    # Build a sensible App.jsx using discovered components (or fallback to 'Main')
    if components:
        component_imports = '\n'.join([f"import {comp} from './components/{comp}.jsx';" for comp in components])
        component_jsx = '\n      '.join([f"<{comp} />" for comp in components])
        files["src/App.jsx"] = f"import React from 'react';\n{component_imports}\n\nfunction App() {{\n  return (\n    <div className=\"min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900\">\n      <div className=\"container mx-auto px-4 py-6 md:py-8 lg:py-12\">\n        {component_jsx}\n      </div>\n    </div>\n  );\n}}\n\nexport default App;"
    else:
        # previous single Main fallback
        components = ['Main']
        files["src/App.jsx"] = """import React from 'react';
import Main from './components/Main.jsx';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="container mx-auto px-4 py-6 md:py-8 lg:py-12">
        <Main />
      </div>
    </div>
  );
}

export default App;
"""

        files["src/components/Main.jsx"] = """import React from 'react';

function Main() {
  return (
    <div className="bg-gradient-to-br from-gray-800 to-gray-700 rounded-xl shadow-2xl p-4 md:p-6 lg:p-8 mb-4 md:mb-6">
      <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-orange-400 mb-4">Main</h2>
      <p className="text-lg md:text-xl text-gray-300 leading-relaxed">This is the Main component.</p>
      <button className="mt-4 bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 px-6 rounded-lg min-h-[44px] transition-colors duration-200">
        Learn More
      </button>
    </div>
  );
}

export default Main;
"""

    return files


async def build_react_app(project_id: str, app_id: str, files: Dict[str, str]) -> Dict[str, any]:
    """
    Build React app by writing files to disk and running npm locally.
    On Vercel, npm is not available at runtime - gracefully degrades to StackBlitz preview.
    
    Args:
        project_id: Internal project ID for tracking
        app_id: Public app ID for preview naming
        files: Dict of filename -> content for the React project
    
    Returns:
        Dict with build_success, dist_url/preview_url, error_message
    """
    import subprocess
    from pathlib import Path
    import shutil
    
    try:
        print(f"📦 Building React app for {app_id}...")
        
        # Check if npm is available
        npm_available = False
        try:
            result = subprocess.run(
                "npm --version",
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            npm_available = result.returncode == 0
        except Exception:
            npm_available = False
        
        if not npm_available:
            # npm not available (Vercel production) - save files for StackBlitz preview
            print(f"   ⚠️ npm not available (Vercel serverless) - saving files for StackBlitz preview")
            
            # Save files to a temporary location so they can be served
            preview_dir = Path(f"/tmp/previews/{app_id}/stackblitz")
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            for filename, content in files.items():
                filepath = preview_dir / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)
            
            # Return a URL to the StackBlitz preview page that will be served by preview route
            return {
                "build_success": True,
                "build_output": "Using StackBlitz preview (npm not available in serverless)",
                "error_message": None,
                "dist_url": f"/api/preview/stackblitz/{app_id}",
                "preview_method": "stackblitz"
            }
        
        # npm is available - proceed with local build
        
        # Create project directory (use /tmp for Vercel serverless)
        project_dir = Path(f"/tmp/previews/{app_id}/build")
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Write all files to disk
        for filename, content in files.items():
            filepath = project_dir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
        
        print(f"   ✓ Wrote {len(files)} files to {project_dir}")
        
        # Modify vite.config.js to include correct base path
        vite_config_path = project_dir / "vite.config.js"
        if vite_config_path.exists():
            vite_content = vite_config_path.read_text()
            # Inject base path into the config
            base_path = f"/preview/{app_id}/dist/"
            vite_content = vite_content.replace(
                "export default defineConfig({",
                f"export default defineConfig({{\n  base: '{base_path}',"
            )
            vite_config_path.write_text(vite_content)
            print(f"   ✓ Set vite base path to {base_path}")

        
        # Run npm install
        print(f"   → npm install...")
        result = subprocess.run(
            "npm install --legacy-peer-deps",
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=120,
            shell=True
        )
        
        if result.returncode != 0:
            error = result.stderr or result.stdout
            print(f"   ❌ npm install failed: {error}")
            return {
                "build_success": False,
                "build_output": result.stdout + result.stderr,
                "error_message": f"npm install failed: {error}",
                "dist_url": None
            }
        
        print(f"   ✓ npm install complete")
        
        # Run npm build
        print(f"   → npm run build...")
        result = subprocess.run(
            "npm run build",
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=120,
            shell=True
        )
        
        if result.returncode != 0:
            error = result.stderr or result.stdout
            print(f"   ❌ npm run build failed: {error}")
            return {
                "build_success": False,
                "build_output": result.stdout + result.stderr,
                "error_message": f"npm build failed: {error}",
                "dist_url": None
            }
        
        print(f"   ✓ npm build complete")
        
        # Check if dist directory exists
        dist_dir = project_dir / "dist"
        if not dist_dir.exists():
            return {
                "build_success": False,
                "error_message": "Build completed but dist/ directory not found",
                "build_output": result.stdout,
                "dist_url": None
            }
        
        # Move dist to preview directory (for serving)
        preview_dist = Path(f"/tmp/previews/{app_id}/dist")
        if preview_dist.exists():
            shutil.rmtree(preview_dist)
        shutil.move(str(dist_dir), str(preview_dist))
        
        # Cleanup build artifacts
        shutil.rmtree(project_dir)
        
        print(f"✅ Build successful for {app_id}")
        
        return {
            "build_success": True,
            "build_output": result.stdout,
            "error_message": None,
            "dist_url": f"/preview/{app_id}/dist/index.html",
            "preview_method": "local"
        }
    
    except subprocess.TimeoutExpired:
        print(f"❌ Build timeout (exceeded 120s)")
        return {
            "build_success": False,
            "build_output": "",
            "error_message": "Build timeout - npm install or build took too long",
            "dist_url": None
        }
    
    except Exception as e:
        print(f"❌ Build error: {e}")
        return {
            "build_success": False,
            "build_output": str(e),
            "error_message": str(e),
            "dist_url": None
        }


def generate_stackblitz_url(app_id: str, files: Dict[str, str]) -> str:
    """
    Generate an HTML page that creates a StackBlitz project with auto-submit form.
    StackBlitz doesn't allow direct URL-based project creation without a backend,
    so we return HTML that posts the files to StackBlitz's API.
    
    Args:
        app_id: Project ID
        files: Generated file contents
    
    Returns:
        HTML content with auto-submitting form to StackBlitz
    """
    import json
    
    # Prepare files for StackBlitz format
    # StackBlitz expects files in format: "filename" -> "content"
    stackblitz_files = {}
    for filename, content in files.items():
        stackblitz_files[filename] = content
    
    # Create the project data payload
    project_data = {
        "files": stackblitz_files,
        "template": "node",
        "title": f"Bridge IDE - {app_id}",
        "description": "Generated React App Preview"
    }
    
    # Generate HTML with auto-submitting form
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Opening Preview...</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: #f5f5f5;
            }}
            .container {{
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                margin-bottom: 10px;
            }}
            p {{
                color: #666;
                margin: 10px 0;
            }}
            .spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .button {{
                background: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin-top: 20px;
            }}
            .button:hover {{
                background: #2980b9;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Opening Preview...</h1>
            <p>Creating your React app preview on StackBlitz</p>
            <div class="spinner"></div>
            <p>If the page doesn't open automatically, click the button below:</p>
            <form id="stackblitz-form" method="post" action="https://stackblitz.com/api/v1/project" target="_blank">
                <button type="submit" class="button">Open on StackBlitz</button>
            </form>
        </div>
        
        <script>
            // Prepare the project data
            const projectData = {json.dumps(project_data)};
            
            // Set form fields for each file
            const form = document.getElementById('stackblitz-form');
            
            Object.entries(projectData.files).forEach(([filename, content]) => {{
                const input = document.createElement('textarea');
                input.name = 'files[' + filename + ']';
                input.value = content;
                form.appendChild(input);
            }});
            
            // Add other project settings
            const titleInput = document.createElement('input');
            titleInput.type = 'hidden';
            titleInput.name = 'title';
            titleInput.value = projectData.title;
            form.appendChild(titleInput);
            
            const templateInput = document.createElement('input');
            templateInput.type = 'hidden';
            templateInput.name = 'template';
            templateInput.value = projectData.template;
            form.appendChild(templateInput);
            
            const descInput = document.createElement('input');
            descInput.type = 'hidden';
            descInput.name = 'description';
            descInput.value = projectData.description;
            form.appendChild(descInput);
            
            // Auto-submit the form after a short delay
            setTimeout(() => {{
                form.submit();
            }}, 500);
        </script>
    </body>
    </html>
    """
    
    return html_content
