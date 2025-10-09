# agents/team.py
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from .tools import ReadFiles, WriteText, RunTests

PM = LlmAgent(
  name="ProjectManager",
  model="gemini-2.0-pro",
  instruction="Take business requirements; produce user stories, acceptance criteria, and task breakdown as YAML.",
  output_key="pm_spec")

Architect = LlmAgent(
  name="SoftwareArchitect",
  model="gemini-2.0-pro",
  instruction=("Read repo and {pm_spec}. Propose technical design, refactors, and perf improvements. "
               "Emit 'dev_plan' with file edits and rationale."),
  tools=[ReadFiles], output_key="dev_plan")

Developer = LlmAgent(
  name="Developer",
  model="gemini-2.0-flash",
  instruction=("Implement {dev_plan}. When changing files, call WriteText(path, content). "
               "Only touch project files."),
  tools=[WriteText])

Tester = LlmAgent(
  name="Tester",
  model="gemini-2.0-flash",
  instruction=("Run tests via RunTests(); summarize failures; set state['quality_status']='pass' or 'fail'."),
  tools=[RunTests], output_key="test_report")

FixUntilGreen = LoopAgent(
  name="FixUntilGreen",
  sub_agents=[Developer, Tester],
  max_iterations=5)

Documenter = LlmAgent(
  name="Documenter",
  model="gemini-2.0-pro",
  instruction=("Create/update docs under docs/AI/: "
               "requirements/, design/, tests/, changelog/. Include test_report and links to changed files."),
  tools=[WriteText])

ShipFlow = SequentialAgent(
  name="ShipFlow",
  sub_agents=[PM, Architect, FixUntilGreen, Documenter])
