"""
Arrivy CRM Sync Migration Crew

This CrewAI configuration is specifically designed to migrate Arrivy from legacy sync patterns 
to the enterprise CRM sync architecture documented in docs/crm_sync_guide.md.

Key Migration Goals:
1. Remove custom Arrivy_SyncHistory and migrate to standardized SyncHistory table
2. Restructure code following ingestion/sync/arrivy/ modular architecture  
3. Implement BaseSyncEngine patterns with bulk operations and proper error handling
4. Replace individual sync_arrivy_*.py commands with unified sync engine
5. Ensure full compliance with CRM sync guide mandatory requirements

Legacy Components to Remove:
- ingestion/management/commands/sync_arrivy_*.py (all individual command files)
- ingestion/models/arrivy.py Arrivy_SyncHistory model
- Custom sync tracking patterns throughout the codebase

New Architecture to Implement:
- ingestion/sync/arrivy/ with clients/, engines/, processors/ subdirectories
- Standardized SyncHistory usage for all sync operations
- Unified management command with --entity-type parameter
- Delta sync using SyncHistory.end_time timestamps
- Enterprise error handling and monitoring patterns
"""

from crewai import Agent, Task, Crew
from textwrap import dedent
import os

# Load your OpenAI key from .env (make sure it's passed into the container environment)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# --- Define Agents ---

arrivy_migration_agent = Agent(
    role='CRM Sync Migration Specialist',
    goal='Migrate Arrivy from legacy sync patterns to enterprise CRM sync architecture',
    backstory=dedent("""
        You are an expert in CRM sync architecture following the enterprise patterns documented in crm_sync_guide.md.
        Your mission is to completely refactor Arrivy's legacy sync implementation to use:
        - Standardized SyncHistory table (instead of Arrivy_SyncHistory)
        - Modular sync engine architecture with separation of concerns
        - Bulk upsert operations with proper error handling
        - Delta sync using SyncHistory.end_time timestamps
        - Unified command structure following BaseSyncEngine patterns
    """),
    verbose=True
)

sync_engine_architect = Agent(
    role='Sync Engine Architecture Designer',
    goal='Create standardized Arrivy sync engines following ingestion/sync/{crm_name}/ structure',
    backstory=dedent("""
        You design enterprise-grade sync engines following the mandatory architecture:
        ingestion/sync/arrivy/
        ├── clients/              # API clients (ArrivyClient refactored)
        ├── engines/             # Sync orchestration engines  
        ├── processors/          # Data transformation and validation
        └── validators.py        # Arrivy-specific validation rules
        
        You ensure proper separation of concerns, async operations, and SyncHistory integration.
    """),
    verbose=True
)

legacy_cleanup_agent = Agent(
    role='Legacy Code Cleanup Specialist',
    goal='Remove old Arrivy sync commands and custom SyncHistory implementation',
    backstory=dedent("""
        You identify and safely remove legacy code patterns that violate the CRM sync guide:
        - Delete individual sync_arrivy_*.py command files
        - Remove Arrivy_SyncHistory model and migrate to standardized SyncHistory
        - Create database migrations to handle data migration
        - Ensure backward compatibility during the transition
    """),
    verbose=True
)

sync_validation_agent = Agent(
    role='CRM Sync Compliance Validator',
    goal='Ensure Arrivy implementation follows all mandatory CRM sync guide requirements',
    backstory=dedent("""
        You validate that the refactored Arrivy implementation strictly follows crm_sync_guide.md:
        - MANDATORY SyncHistory usage (no custom sync tracking)
        - Proper delta sync using SyncHistory.end_time
        - Standard command-line flags (--full, --force, --since, --dry-run)
        - Bulk operations with conflict resolution
        - Enterprise error handling and monitoring
    """),
    verbose=True
)

data_migration_agent = Agent(
    role='Data Migration Strategist',
    goal='Create safe migration path from Arrivy_SyncHistory to standardized SyncHistory',
    backstory=dedent("""
        You create foolproof data migration strategies to move from legacy sync tracking to 
        standardized SyncHistory without losing sync state or causing downtime.
        You handle schema changes, data mapping, and rollback procedures.
    """),
    verbose=True
)

# --- Define Tasks ---

arrivy_migration_task = Task(
    description="""
        Completely migrate Arrivy from legacy sync patterns to enterprise CRM sync architecture:
        
        1. **Remove Legacy Infrastructure:**
           - Delete all sync_arrivy_*.py command files (sync_arrivy_entities.py, sync_arrivy_tasks.py, etc.)
           - Remove Arrivy_SyncHistory model from ingestion/models/arrivy.py
           - Create migration to drop arrivy_sync_history table
        
        2. **Implement Standardized Architecture:**
           - Create ingestion/sync/arrivy/ directory structure following crm_sync_guide.md
           - Move ArrivyClient to ingestion/sync/arrivy/clients/base.py
           - Create entity-specific clients (entities.py, tasks.py, groups.py)
           - Implement sync engines with proper SyncHistory integration
           - Add processors for data transformation and validation
        
        3. **Ensure SyncHistory Compliance:**
           - Use standardized SyncHistory model only (NO custom sync tracking)
           - Implement delta sync using SyncHistory.end_time timestamps
           - Follow standard field formats (crm_source='arrivy', sync_type='entities', etc.)
    """,
    expected_output="Complete refactored Arrivy sync architecture following crm_sync_guide.md with all legacy code removed.",
    agent=arrivy_migration_agent
)

sync_engine_architecture_task = Task(
    description="""
        Design and implement the standardized sync engine architecture for Arrivy:
        
        1. **Create Modular Structure:**
           ingestion/sync/arrivy/
           ├── clients/base.py          # Refactored ArrivyClient
           ├── clients/entities.py      # Entity-specific API client
           ├── clients/tasks.py         # Task-specific API client  
           ├── clients/groups.py        # Group-specific API client
           ├── engines/base.py          # ArrivyBaseSyncEngine
           ├── engines/entities.py     # Entity sync orchestration
           ├── engines/tasks.py        # Task sync orchestration
           ├── engines/groups.py       # Group sync orchestration
           ├── processors/base.py      # Base data processor
           ├── processors/entities.py  # Entity data transformation
           ├── processors/tasks.py     # Task data transformation
           └── validators.py           # Arrivy-specific validation
        
        2. **Implement BaseSyncEngine Pattern:**
           - Async orchestration with proper error handling
           - Bulk upsert operations using bulk_create(update_conflicts=True)
           - Standard command-line flags support
           - SyncHistory integration for all operations
        
        3. **Create Unified Management Commands:**
           - Single management/commands/sync_arrivy.py with entity type parameter
           - Replace all individual sync_arrivy_*.py commands
           - Support --entity-type=entities,tasks,groups,all parameter
    """,
    expected_output="Complete modular sync engine architecture with separation of concerns and enterprise patterns.",
    agent=sync_engine_architect
)

legacy_cleanup_task = Task(
    description="""
        Safely remove all legacy Arrivy sync code and migrate to standardized patterns:
        
        1. **Identify Legacy Components:**
           - List all sync_arrivy_*.py command files for removal
           - Identify Arrivy_SyncHistory model usage throughout codebase
           - Find any custom sync tracking fields in Arrivy models
        
        2. **Create Safe Migration Path:**
           - Create Django migration to copy Arrivy_SyncHistory data to SyncHistory
           - Map old sync_type values to new standardized format
           - Ensure no data loss during migration
        
        3. **Remove Legacy Code:**
           - Delete individual sync command files after migration
           - Remove Arrivy_SyncHistory model from arrivy.py
           - Clean up imports and references
           - Update __all__ exports in models/__init__.py
        
        4. **Backward Compatibility:**
           - Document migration steps for production deployment
           - Create rollback procedures if needed
           - Test migration with sample data
    """,
    expected_output="Comprehensive cleanup plan with safe data migration and legacy code removal procedures.",
    agent=legacy_cleanup_agent
)

sync_validation_task = Task(
    description="""
        Validate that the refactored Arrivy implementation follows ALL mandatory requirements from crm_sync_guide.md:
        
        1. **SyncHistory Compliance Validation:**
           - Verify SyncHistory table usage (NO custom sync tracking)
           - Check proper field formats (crm_source='arrivy', sync_type without '_sync' suffix)
           - Validate status field uses standard values ('running', 'success', 'failed', 'partial')
           - Ensure end_time is used for delta sync timestamps
        
        2. **Architecture Compliance:**
           - Verify modular structure follows ingestion/sync/{crm_name}/ pattern
           - Check separation of clients, engines, and processors
           - Validate async orchestration implementation
           - Ensure bulk operations with proper conflict resolution
        
        3. **Command-Line Interface:**
           - Verify standard flags (--full, --force, --since, --dry-run, --batch-size)
           - Check --entity-type parameter for unified command
           - Validate flag behavior matches crm_sync_guide.md specifications
        
        4. **Error Handling & Monitoring:**
           - Check enterprise error handling patterns
           - Verify SyncHistory status updates on failures
           - Validate performance metrics collection
    """,
    expected_output="Comprehensive compliance validation report with checklist confirming all crm_sync_guide.md requirements.",
    agent=sync_validation_agent
)

data_migration_task = Task(
    description="""
        Create bulletproof data migration strategy from Arrivy_SyncHistory to standardized SyncHistory:
        
        1. **Data Mapping Strategy:**
           - Map Arrivy_SyncHistory.sync_type to SyncHistory format
           - Convert last_synced_at to end_time with proper timezone handling
           - Ensure crm_source='arrivy' for all migrated records
           - Handle any missing required fields with sensible defaults
        
        2. **Migration Implementation:**
           - Create Django migration with data copying logic
           - Handle large datasets with batching to avoid memory issues
           - Implement validation to ensure data integrity
           - Create backup procedures for rollback capability
        
        3. **Production Deployment Plan:**
           - Zero-downtime migration strategy
           - Pre-migration validation checks
           - Post-migration verification procedures
           - Monitoring for sync operations during transition
        
        4. **Rollback Procedures:**
           - Document exact steps to revert if issues occur
           - Create scripts to restore original functionality
           - Test rollback procedures in staging environment
    """,
    expected_output="Complete data migration plan with implementation code, deployment procedures, and rollback strategies.",
    agent=data_migration_agent
)

# --- Define Crew ---

crew = Crew(
    agents=[arrivy_migration_agent, sync_engine_architect, legacy_cleanup_agent, sync_validation_agent, data_migration_agent],
    tasks=[arrivy_migration_task, sync_engine_architecture_task, legacy_cleanup_task, sync_validation_task, data_migration_task],
    verbose=True
)

if __name__ == '__main__':
    crew.kickoff()