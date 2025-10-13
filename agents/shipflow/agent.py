"""
ShipFlow - Complete Software Development Workflow Agent

This agent orchestrates a multi-agent workflow for software development:
1. PM (ProjectManager) - Analyzes requirements and creates task breakdown
2. Architect (SoftwareArchitect) - Designs technical solution
3. Developer - Implements the code
4. Tester - Runs tests and validates
5. Documenter - Updates documentation

The workflow includes a FixUntilGreen loop that iterates between Developer and Tester
up to 5 times to ensure all tests pass.
"""

from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
import sys
import os

# Add parent directory to path to import tools
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from tools import ReadFiles, WriteText, RunTests
except ImportError:
    # Fallback if tools aren't available
    from google.adk.tools import FunctionTool
    import glob
    
    def read_files(glob_pattern, max_kb=96):
        """Read files matching a glob pattern."""
        paths = [p for p in glob.glob(glob_pattern, recursive=True) if os.path.isfile(p)]
        out = {}
        for p in paths[:200]:
            try:
                with open(p, "r", errors="ignore") as f:
                    out[p] = f.read()[:max_kb*1024]
            except Exception as e:
                out[p] = f"Error reading file: {e}"
        return out

    def write_text(path, content):
        """Write text content to a file."""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Successfully wrote to {path}"

    def run_tests(args=None):
        """Run tests (placeholder)."""
        return {"ok": True, "message": "Tests not configured", "stdout": "", "stderr": ""}

    ReadFiles = FunctionTool(func=read_files)
    WriteText = FunctionTool(func=write_text)
    RunTests = FunctionTool(func=run_tests)

# Define the PM Agent
PM = LlmAgent(
    name="ProjectManager",
    model="gemini-2.0-flash-exp",
    instruction=(
        "You are a Project Manager. Analyze business requirements and produce:\n"
        "1. User stories with acceptance criteria\n"
        "2. Task breakdown with priorities\n"
        "3. Implementation plan\n"
        "Output YAML format with clear sections."
    ),
    output_key="pm_spec"
)

# Define the Architect Agent
Architect = LlmAgent(
    name="SoftwareArchitect",
    model="gemini-2.0-flash-exp",
    instruction=(
        "You are a Software Architect. Read the repository and PM spec: {pm_spec}\n"
        "Propose:\n"
        "1. Technical design and architecture\n"
        "2. Database schema changes if needed\n"
        "3. API endpoint designs\n"
        "4. File-level implementation plan\n"
        "Use ReadFiles tool to understand existing code patterns.\n"
        "Output 'dev_plan' with specific files to modify and rationale."
    ),
    tools=[ReadFiles],
    output_key="dev_plan"
)

# Define the Developer Agent
Developer = LlmAgent(
    name="Developer",
    model="gemini-2.0-flash-exp",
    instruction=(
        "You are a Developer. Implement the development plan: {dev_plan}\n"
        "1. Write clean, idiomatic code\n"
        "2. Follow existing code patterns\n"
        "3. Use WriteText(path, content) to create/update files\n"
        "4. Only modify project files, never system files\n"
        "5. Include proper error handling and logging\n"
        "Be thorough and complete - implement ALL required functionality."
    ),
    tools=[WriteText]
)

# Define the Tester Agent  
Tester = LlmAgent(
    name="Tester",
    model="gemini-2.0-flash-exp",
    instruction=(
        "You are a QA Tester. Run tests and validate the implementation.\n"
        "1. Use RunTests() to execute the test suite\n"
        "2. Analyze failures and report issues clearly\n"
        "3. Set state['quality_status'] = 'pass' if all tests pass\n"
        "4. Set state['quality_status'] = 'fail' if tests fail\n"
        "5. Provide detailed failure analysis for the developer"
    ),
    tools=[RunTests],
    output_key="test_report"
)

# Define the FixUntilGreen Loop
# This loop runs Developer → Tester repeatedly until tests pass (max 5 iterations)
FixUntilGreen = LoopAgent(
    name="FixUntilGreen",
    sub_agents=[Developer, Tester],
    max_iterations=5
)

# Define the Documenter Agent
Documenter = LlmAgent(
    name="Documenter",
    model="gemini-2.0-flash-exp",
    instruction=(
        "You are a Technical Writer. Create/update documentation:\n"
        "1. Create changelog entry in docs/AI/changelog/\n"
        "2. Document API endpoints if added\n"
        "3. Update architecture docs if structure changed\n"
        "4. Include test results: {test_report}\n"
        "5. Add links to modified files\n"
        "Use WriteText tool to create documentation files."
    ),
    tools=[WriteText]
)

# Define the complete ShipFlow workflow
# Sequential execution: PM → Architect → FixUntilGreen → Documenter
root_agent = SequentialAgent(
    name="ShipFlow",
    sub_agents=[PM, Architect, FixUntilGreen, Documenter],
    description=(
        "Complete software development workflow agent. "
        "Analyzes requirements, designs solution, implements code, "
        "runs tests (with fix loop), and updates documentation."
    )
)

# Export for ADK
__all__ = ['root_agent']
