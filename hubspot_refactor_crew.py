from crewai import Agent, Task, Crew
from textwrap import dedent
import os

# Load your OpenAI key from .env (make sure it's passed into the container environment)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# --- Define Agents ---

dev_agent = Agent(
    role='Senior Python Developer',
    goal='Refactor all entity sync engines using modern patterns',
    backstory=dedent("""
        You are a backend Python expert familiar with Django async, bulk operations, and MDM design patterns.
        Your job is to update all sync commands to use true bulk upsert, modular engines, and error-handling best practices.
    """),
    verbose=True
)

qa_agent = Agent(
    role='QA Automation Engineer',
    goal='Ensure full test coverage and behavior consistency across all engines',
    backstory=dedent("""
        You specialize in automated testing for Django-based data platforms.
        You will write new tests for sync commands and processors and ensure coverage for edge cases.
    """),
    verbose=True
)

db_agent = Agent(
    role='Database Optimization Specialist',
    goal='Review database schema and recommend index improvements for upsert performance',
    backstory=dedent("""
        You are a PostgreSQL and Django ORM expert who ensures every upsert and filter operation is backed by the right index.
    """),
    verbose=True
)

doc_agent = Agent(
    role='Technical Documentation Writer',
    goal='Update import_refactoring.md with new architecture patterns',
    backstory=dedent("""
        You specialize in developer onboarding and enterprise coding standards. 
        Your task is to capture the latest sync architecture and write how-to guidance.
    """),
    verbose=True
)

deprecation_agent = Agent(
    role='Legacy Migration Steward',
    goal='Identify and deprecate legacy commands and patterns',
    backstory=dedent("""
        You maintain backward compatibility and document deprecated patterns with migration paths for developers.
    """),
    verbose=True
)

# --- Define Tasks ---

refactor_task = Task(
    description="""
        Refactor all HubSpot-related entity syncs (deals, divisions, associations) to use
        bulk_create(update_conflicts=True) and async orchestration. Apply separation of engine, processor, and client.
    """,
    expected_output="Refactored Python code for sync commands following bulk upsert and async patterns.",
    agent=dev_agent
)

testing_task = Task(
    description="""
        Write or improve test coverage for all entity sync engines, especially those recently
        refactored for bulk upsert or async behavior. Use Django TestCase or Pytest with mocking where needed.
    """,
    expected_output="New or updated test files for sync engines with minimum 80% coverage and test case documentation.",
    agent=qa_agent
)

db_task = Task(
    description="""
        Analyze all unique fields involved in upserts and filtering. Suggest or add appropriate indexes
        in Django models (Meta.indexes or unique_together). Document performance tips if needed.
    """,
    expected_output="List of fields with indexing recommendations and example Django Meta configurations.",
    agent=db_agent
)

docs_task = Task(
    description="""
        Update import_refactoring.md to document:
        - async orchestration
        - bulk upsert
        - separation of engine/processor/client
        - error handling standards
        - CLI args (batch-size, dry-run)
        Include examples and mark deprecated patterns.
    """,
    expected_output="Markdown text to update import_refactoring.md reflecting new architecture and examples.",
    agent=doc_agent
)

deprecation_task = Task(
    description="""
        Identify legacy sync commands or logic. Mark them with deprecation warnings.
        Add migration guidance to import_refactoring.md or a new MIGRATIONS.md file.
    """,
    expected_output="List of deprecated patterns and corresponding migration paths with code snippets.",
    agent=deprecation_agent
)

# --- Define Crew ---

crew = Crew(
    agents=[dev_agent, qa_agent, db_agent, doc_agent, deprecation_agent],
    tasks=[refactor_task, testing_task, db_task, docs_task, deprecation_task],
    verbose=True
)

if __name__ == '__main__':
    crew.kickoff()