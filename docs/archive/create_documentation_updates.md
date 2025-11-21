You are an AI documentation assistant.

Your task is to generate a new file called `update_documentation_todo.md` that contains a complete and actionable documentation-update plan for the magrhino/shelfarr project.

Your plan must instruct an AI agent how to update all project documentation based on the latest architecture described in:

    @docs/jinja_migration_changes.md
    @docs/css_refactoring_summary.md

Both of these files reflect the current state of the codebase after the legacy → Vue migration and the CSS refactor.

Your goal is to:
1. Update `@README.md` to remove outdated references to mam-audiofinder, update architecture descriptions, and reflect the new Vue + Naive UI frontend.
2. Update `@docs/BACKEND.md` to reflect the current backend architecture after Jinja deprecation and route changes.
3. Create a new `@docs/FRONTEND.md` describing the modern frontend architecture including:
   - Project layout
   - Vue components and view structure
   - Naive UI theme system
   - global.css + main.css roles
   - Component-scoped styling
   - Frontend build workflow
   - migration status (legacy → Vue)
4. Ensure all documentation references the current CSS architecture:
   - main.css (minimal base)
   - legacy.css (temporary, being removed)
   - global.css (Vue global)
   - component-scoped styles
   - Naive UI theme overrides
5. Ensure all documentation references the current application architecture:
   - Vue SPA is primary entrypoint
   - Flask backend only handles API + SPA index.html
   - Legacy templates no longer used (except possibly transitional)
6. Remove or rewrite sections referencing old Flask/Jinja UI.
7. Ensure naming conventions match the current project (`shelfarr`, not `mam-audiofinder`).

The resulting file `update_documentation_todo.md` must include:

## Mandatory Structure

- Title section: “Documentation Update TODO”
- Summary of why documentation needs updating
- A section for README.md changes  
  (explicit bullet points listing additions, deletions, rewrites)
- A section for BACKEND.md updates  
  (architecture, API routes, dependency updates, removed templates)
- A section for FRONTEND.md creation  
  (what topics the agent must include, what subheaders to use)
- A list of all files the agent must open, read, or generate
- A list of outdated text patterns to remove (e.g., “mam-audiofinder”)
- A QA checklist for validating the updated docs

## Output Requirements

- Produce **one Markdown file** named `update_documentation_todo.md` at docs/
- Use clear, numbered tasks intended for AI agent execution
- Use short actionable descriptions ("Replace X with Y", "Search for phrase ___ and delete", etc.)
- Include checkboxes for each step

Begin now.
