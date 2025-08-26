Looking at your codebase, I'll analyze each CRM integration's SyncHistory compliance. Based on my review, most integrations are NOT using SyncHistory properly and need significant updates.

Current SyncHistory Compliance Status:
❌ Non-Compliant (Need Major Updates)
Arrivy - Still has legacy sync_updated_at/sync_created_at fields, no SyncHistory integration
Five9 - No evidence of SyncHistory usage
Genius - Legacy sync patterns, no SyncHistory integration
GSheet - No SyncHistory integration found
LeadConduit - No SyncHistory integration found
SalesPro - No SyncHistory integration found
SalesRabbit - No SyncHistory integration found
✅ Partially Compliant
CallRail - Has some SyncHistory usage but may need updates
HubSpot - Has some SyncHistory usage but may need updates
Your Requirements are Clear:
Individual Entity Records: Each sync operation should create separate SyncHistory entries per entity type (e.g., sync_type='contacts', sync_type='deals', sync_type='calls')
No "All" Entries: When running sync_all commands, create individual SyncHistory records for each sub-entity, not one record for "all"
Required Actions:
For each non-compliant CRM, you need to:

Would you like me to start refactoring a specific CRM integration (like Arrivy) to demonstrate the complete SyncHistory migration pattern?