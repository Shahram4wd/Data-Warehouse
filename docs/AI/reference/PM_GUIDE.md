# PM Reference Guide

**Document Version**: 1.0  
**Last Updated**: 2025  
**Purpose**: Reference guide for Product Managers and AI agents to create clear, actionable requirements

---

## Table of Contents
1. [Requirements Template](#requirements-template)
2. [User Story Format](#user-story-format)
3. [Acceptance Criteria](#acceptance-criteria)
4. [CRM Integration Requirements](#crm-integration-requirements)
5. [Dashboard Feature Requirements](#dashboard-feature-requirements)
6. [Bug Report Template](#bug-report-template)
7. [Feature Request Template](#feature-request-template)

---

## Requirements Template

### Standard Requirement Format

```markdown
# [Feature/Component Name]

## Overview
Brief description of what this feature does and why it's needed.

## User Story
As a [type of user],
I want to [perform some action],
So that I can [achieve some goal/benefit].

## Acceptance Criteria
1. Given [context], when [action], then [expected result]
2. Given [context], when [action], then [expected result]
3. ...

## Technical Requirements
- Component: [Django app, service, model, etc.]
- Dependencies: [Other features or systems]
- Performance: [Response time, throughput requirements]
- Security: [Auth, permissions, data protection]

## Implementation Notes
- Architecture decisions
- Design patterns to follow
- Integration points

## Testing Requirements
- Unit test coverage: [X%]
- Integration tests: [specific scenarios]
- Manual testing steps

## Documentation
- Update these files: [list]
- Add API documentation
- Update user guide

## Definition of Done
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Deployed to staging
- [ ] PM approval received
```

---

## User Story Format

### Structure

**As a** [role]  
**I want to** [capability]  
**So that** [benefit/value]

### Examples for Data Warehouse

#### Example 1: CRM Sync Feature
```
As a Data Analyst,
I want to sync HubSpot contacts automatically every hour,
So that I can analyze up-to-date customer data without manual exports.

Acceptance Criteria:
- Schedule created for hourly sync at :00 minute
- Delta sync runs (only new/updated records)
- Sync completes within 5 minutes
- SyncHistory record created with metrics
- Dashboard shows "Last Sync: X minutes ago"
- Email alert sent if sync fails
```

#### Example 2: Dashboard Enhancement
```
As a Marketing Manager,
I want to see a summary card showing total CallRail calls this month,
So that I can quickly assess call volume trends.

Acceptance Criteria:
- Card displays on CRM Dashboard home page
- Shows total calls for current month
- Compares to previous month (% change)
- Updates in real-time when syncs complete
- Click card to navigate to CallRail calls detail page
- Card shows loading state while data fetches
```

#### Example 3: Bug Fix
```
As a System Administrator,
I want sync_hubspot_genius_users to correctly store record counts in SyncHistory,
So that the dashboard accurately reflects sync results.

Acceptance Criteria:
- SyncHistory.records_processed matches actual processed count
- SyncHistory.records_created matches new records
- SyncHistory.records_updated matches updated records
- Dashboard summary cards show correct "Just now" timestamp
- No records show 0 for all counts when sync succeeds
```

---

## Acceptance Criteria

### INVEST Criteria

Good acceptance criteria are:
- **Independent**: Can be tested in isolation
- **Negotiable**: Details can be refined
- **Valuable**: Delivers user value
- **Estimable**: Can estimate effort
- **Small**: Fits in one sprint
- **Testable**: Clear pass/fail

### Format: Given-When-Then

```
Given [initial context/state],
When [action is performed],
Then [expected outcome].
```

### Examples

#### Sync Operation Acceptance Criteria
```
AC1: Successful Full Sync
Given a HubSpot API key is configured,
When I run "python manage.py sync_hubspot_contacts --full",
Then all HubSpot contacts are fetched and saved to the database.

AC2: Sync History Tracking
Given a sync operation completes successfully,
When I check the SyncHistory table,
Then a record exists with status='success' and accurate record counts.

AC3: Error Handling
Given the HubSpot API returns a 429 rate limit error,
When the sync engine encounters this error,
Then it waits for the retry-after period and resumes the sync.

AC4: Dry Run Mode
Given I want to test a sync without saving data,
When I run the command with "--dry-run",
Then data is fetched and logged but not saved to the database.
```

#### Dashboard Feature Acceptance Criteria
```
AC1: CRM List Display
Given I navigate to /dashboard/,
When the page loads,
Then I see a card for each CRM source (HubSpot, CallRail, Genius, etc.).

AC2: Model Count Display
Given a CRM has models with data,
When I view the CRM card,
Then I see the total record count across all models for that CRM.

AC3: Sync Status Indicator
Given a sync is currently running for a CRM,
When I view the dashboard,
Then I see a "Syncing..." badge with a spinner icon.

AC4: Navigation
Given I click on a CRM card,
When the click is processed,
Then I am navigated to /dashboard/{crm_source}/models/.
```

---

## CRM Integration Requirements

### New CRM Integration Template

```markdown
# [CRM Name] Integration

## Overview
Integrate [CRM Name] to sync [list entities] into the Data Warehouse.

## Business Value
- Why: [Business justification]
- Impact: [Expected outcomes]
- Priority: [High/Medium/Low]

## API Information
- **API Type**: REST / GraphQL / Database / File-based
- **Base URL**: [URL]
- **Authentication**: API Key / OAuth2 / Database credentials
- **Rate Limits**: [X requests per Y time period]
- **Documentation**: [Link to API docs]

## Entities to Sync
1. **[Entity 1]** (e.g., Contacts)
   - Endpoint: [API endpoint or table]
   - Update Frequency: [Real-time / Hourly / Daily]
   - Est. Record Count: [Number]
   - Key Fields: [List important fields]

2. **[Entity 2]** (e.g., Deals)
   - ...

## Data Model
- Django models to create in `ingestion/models/[crm].py`
- Table names: `[crm]_[entity]`
- Key relationships to existing data

## Technical Implementation

### Phase 1: Foundation
- [ ] Create Django models
- [ ] Run migrations
- [ ] Set up API credentials in .env
- [ ] Create base client class
- [ ] Create base processor class

### Phase 2: Sync Engines
- [ ] Implement [Entity1]SyncEngine
- [ ] Implement [Entity2]SyncEngine
- [ ] Create orchestration command (sync_[crm]_all)

### Phase 3: Management Commands
- [ ] Create sync_[crm]_[entity1] command
- [ ] Create sync_[crm]_[entity2] command
- [ ] Add standard flags (--full, --dry-run, --debug)

### Phase 4: Dashboard Integration
- [ ] Add CRM to CRMDiscoveryService.crm_systems
- [ ] Test dashboard displays CRM models
- [ ] Verify sync history tracking

### Phase 5: Testing
- [ ] Unit tests for commands
- [ ] Integration tests with mocked API
- [ ] End-to-end test with real API (controlled data)
- [ ] Add to test_interface.py

### Phase 6: Documentation
- [ ] Create sync/[crm]/README.md
- [ ] Document API endpoints
- [ ] Add usage examples
- [ ] Update main docs

## Acceptance Criteria
1. All entities sync successfully with real API
2. SyncHistory records created for each sync
3. Dashboard displays CRM and models
4. Tests achieve 80%+ coverage
5. Documentation complete

## Success Metrics
- Sync duration: [target time]
- Error rate: < 1%
- Data freshness: [X minutes/hours]
```

---

## Dashboard Feature Requirements

### Dashboard Component Template

```markdown
# Dashboard Feature: [Feature Name]

## Overview
Add [component/feature] to the CRM Dashboard to provide [value].

## User Story
As a [role],
I want [feature],
So that [benefit].

## UI/UX Requirements

### Layout
- Location: [Where on page]
- Size: [Dimensions, responsive behavior]
- Style: [Bootstrap classes, custom CSS]

### Visual Design
- Colors: [Primary, secondary, accent]
- Typography: [Font sizes, weights]
- Icons: [Bootstrap Icons to use]
- States: [Loading, empty, error, success]

### Interactions
1. On page load: [behavior]
2. On user action: [response]
3. On data update: [refresh behavior]

## API Requirements

### Endpoint
- **URL**: `/api/dashboard/[endpoint]/`
- **Method**: GET / POST / PUT / DELETE
- **Auth**: Required / Optional
- **Rate Limit**: [requests per minute]

### Request Format
```json
{
  "param1": "value",
  "param2": "value"
}
```

### Response Format
```json
{
  "success": true,
  "data": {
    ...
  }
}
```

## Backend Requirements

### Service Layer
- Service class: [Name]
- Methods: [List methods needed]
- Database queries: [Describe queries]

### Caching
- Cache key format: [pattern]
- TTL: [duration]
- Invalidation: [when to clear]

## Frontend Requirements

### JavaScript
- Event handlers: [List events]
- AJAX calls: [Endpoints to call]
- DOM manipulation: [What changes]

### Templates
- Template file: [path]
- Template blocks: [List blocks]
- Context variables: [List variables]

## Acceptance Criteria
1. Given [context], when [action], then [result]
2. ...

## Performance Requirements
- Page load: < 2 seconds
- API response: < 500ms
- UI update: < 100ms

## Accessibility
- Keyboard navigation: [requirements]
- Screen reader: [ARIA labels]
- Color contrast: [WCAG compliance]
```

---

## Bug Report Template

```markdown
# Bug: [Short Description]

## Environment
- Branch: [main / develop / feature-xyz]
- Django Version: [version]
- PostgreSQL Version: [version]
- Docker: Yes / No

## Steps to Reproduce
1. Navigate to [URL/command]
2. Perform [action]
3. Observe [result]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Screenshots/Logs
[Attach screenshots, error logs, stack traces]

## Error Messages
```
[Paste error messages here]
```

## Impact
- Severity: Critical / High / Medium / Low
- Affected Users: [All / Specific role / Admin only]
- Workaround: [If available]

## Root Cause Analysis (if known)
[Technical explanation of the bug]

## Proposed Fix
[How to fix it]

## Related Issues
- Related to: #[issue number]
- Blocks: #[issue number]
```

---

## Feature Request Template

```markdown
# Feature Request: [Feature Name]

## Problem Statement
[Describe the problem or pain point]

## Proposed Solution
[Describe the feature and how it solves the problem]

## User Story
As a [role],
I want [capability],
So that [benefit].

## Acceptance Criteria
1. [Criterion 1]
2. [Criterion 2]
3. ...

## Mockups/Wireframes
[Attach UI mockups if applicable]

## Technical Considerations
- Impact on existing features: [describe]
- Dependencies: [list]
- Performance: [concerns]

## Alternatives Considered
1. [Alternative 1]: [pros/cons]
2. [Alternative 2]: [pros/cons]

## Priority
- Business Value: High / Medium / Low
- Technical Complexity: High / Medium / Low
- Urgency: Immediate / Next Sprint / Future

## Success Metrics
- [Metric 1]: [target]
- [Metric 2]: [target]
```

---

## Common Requirement Patterns

### Pattern 1: Add New CRM Entity
```
Title: Add [CRM] [Entity] Sync

Requirements:
1. Create Django model for [Entity]
2. Implement [Entity]SyncEngine
3. Create management command
4. Add to dashboard
5. Write tests

Time Estimate: 2-3 days
```

### Pattern 2: Fix Sync Issue
```
Title: Fix [CRM] [Entity] Sync Statistics

Requirements:
1. Identify root cause in sync engine
2. Fix save_data() or save_data_bulk() method
3. Verify SyncHistory records correct counts
4. Update tests
5. Verify dashboard displays correct data

Time Estimate: 4-8 hours
```

### Pattern 3: Dashboard Enhancement
```
Title: Add [Metric] to Dashboard

Requirements:
1. Create API endpoint to fetch metric
2. Add service method to calculate metric
3. Create dashboard card component
4. Add real-time updates
5. Write frontend and backend tests

Time Estimate: 1-2 days
```

---

## Working with AI Agents

### How to Write Requirements for AI Agents

**DO**:
- ✅ Be specific about file locations
- ✅ Mention existing patterns to follow
- ✅ Specify testing requirements
- ✅ Include examples from codebase
- ✅ Reference related documentation

**DON'T**:
- ❌ Use vague language ("improve performance")
- ❌ Assume agent knows business context
- ❌ Skip acceptance criteria
- ❌ Forget to mention related files

### Example: Good vs Bad Requirements

**❌ Bad Requirement**:
```
Add a new CRM integration for Acme CRM.
```

**✅ Good Requirement**:
```
# Acme CRM Integration

Follow the CRM integration framework documented in docs/AI/reference/ARCHITECTURE.md.

## Models
Create models in ingestion/models/acme.py following the pattern from ingestion/models/hubspot.py.

Entities:
1. Acme_Contact (similar to Hubspot_Contact)
   - Fields: id, email, first_name, last_name, phone, created_at, updated_at
   
2. Acme_Deal (similar to Hubspot_Deal)
   - Fields: id, title, amount, status, close_date, created_at, updated_at

## Sync Engine
Create sync/acme/engines/contacts.py inheriting from BaseSyncEngine (ingestion/base/sync_engine.py).

Implement required methods:
- initialize_client() - Set up API client
- fetch_data() - Fetch from Acme API endpoint: GET /api/v1/contacts
- transform_data() - Map Acme fields to model fields
- validate_data() - Validate required fields
- save_data() - Use bulk_create/bulk_update pattern

## Management Command
Create management/commands/sync_acme_contacts.py following the pattern from sync_hubspot_contacts.py.

Standard flags: --full, --dry-run, --debug, --batch-size

## Testing
- Unit tests in tests/test_crm_acme.py
- Follow pattern from tests/test_crm_hubspot.py
- Test configurations in test_interface.py

## Acceptance Criteria
1. Models created and migrated
2. Sync engine implements all BaseSyncEngine abstract methods
3. Management command has all standard flags
4. Sync creates SyncHistory records
5. Dashboard displays Acme CRM
6. Tests achieve 80%+ coverage
```

---

## Related Documents

- [Architecture Overview](ARCHITECTURE.md)
- [Database Schema Reference](DATABASE_SCHEMA.md)
- [API & Integration Reference](API_INTEGRATIONS.md)
- [Existing Tests Documentation](EXISTING_TESTS.md)
- [Codebase Navigation Map](CODEBASE_MAP.md)

---

**Document Maintained By**: Development Team & AI Agents  
**Last Review**: 2025  
**Next Review**: Quarterly
