# CRM Dashboard Requirements Document

## 📋 **Project Overview**

Create a comprehensive CRM management dashboard under `/ingestion/crm-dashboard/` that provides:
- **CRM Source Overview**: List all CRM modules (genius.py, hubspot.py, etc.)
- **Model Management**: View all models within each CRM with sync status
- **Sync Execution**: Execute sync commands with parameters (--force, --full, --since)
- **Data Visualization**: Table view with pagination for actual model data
- **Real-time Updates**: Live status updates during sync operations

---

## 🗂️ **Data Structure Analysis**

### **SyncHistory Model Structure**
Based on `ingestion/models/common.py`:

```python
class SyncHistory(models.Model):
    # Identification
    crm_source = models.CharField(max_length=50)      # 'genius', 'hubspot', 'callrail', etc.
    sync_type = models.CharField(max_length=100)      # 'appointments', 'contacts', 'prospects', etc.
    endpoint = models.CharField(max_length=200, null=True, blank=True)
    
    # Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Status ('running', 'success', 'failed', 'partial')
    status = models.CharField(max_length=20)
    
    # Metrics
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    
    # Performance & Configuration
    configuration = models.JSONField(default=dict)
    performance_metrics = models.JSONField(default=dict)
```

### **Discovered CRM Models**
From `ingestion/models/` directory:

| CRM Source | Model File | Example Models |
|------------|------------|---------------|
| `genius` | `genius.py` | `GeniusAppointment`, `GeniusProspect`, `GeniusUser`, `GeniusLead`, `GeniusQuote` |
| `hubspot` | `hubspot.py` | `HubspotContact`, `HubspotDeal`, `HubspotAppointment` |
| `callrail` | `callrail.py` | `CallrailCall`, `CallrailAccount`, `CallrailCompany`, `CallrailTracker` |
| `arrivy` | `arrivy.py` | `ArrivyEntity`, `ArrivyTask`, `ArrivyGroup` |
| `leadconduit` | `leadconduit.py` | `LeadconduitLead` |
| `marketsharp` | `marketsharp.py` | Market Sharp models |
| `salespro` | `salespro.py` | `SalesproCustomer`, `SalesproEstimate`, `SalesproPayment`, `SalesproLeadresult` |
| `salesrabbit` | `salesrabbit.py` | `SalesrabbitLead` |
| `gsheet` | `gsheet.py` | Google Sheets models |

### **Management Commands Mapping**
From `ingestion/management/commands/`:

| Pattern | Example Commands | Parameters |
|---------|------------------|------------|
| `sync_{crm}_{model}` | `sync_genius_appointments.py`, `sync_hubspot_contacts.py` | `--force`, `--full`, `--since` |
| `sync_{crm}_all` | `sync_genius_all.py`, `sync_hubspot_all.py` | Same parameters |
| `db_{crm}_{model}` | `db_genius_appointments.py`, `db_salespro_customers.py` | Database-specific commands |

---

## 🎯 **Feature Requirements**

### **1. CRM Overview Page** (`/ingestion/crm-dashboard/`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ CRM Management Dashboard                                     │
├─────────────────────────────────────────────────────────────┤
│ [Search CRM] [Refresh All] [View All Syncs]                │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Genius ──────────────────┐ ┌─ HubSpot ─────────────────┐ │
│ │ 📊 5 Models               │ │ 📊 3 Models               │ │
│ │ ⚡ Last Sync: 2 hrs ago   │ │ ⚡ Last Sync: 1 hr ago    │ │
│ │ ✅ Status: Success        │ │ ⚠️  Status: Partial       │ │
│ │ [View Models]             │ │ [View Models]             │ │
│ └───────────────────────────┘ └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
- **CRM Discovery**: Automatically scan `ingestion/models/` for model files
- **Model Count**: Count Django models in each CRM file
- **Last Sync Status**: Query `SyncHistory` for most recent sync per CRM
- **Status Aggregation**: Determine overall CRM health (success/warning/error)

### **2. CRM Models List Page** (`/ingestion/crm-dashboard/{crm_source}/`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Genius CRM - Models                      [Back to Dashboard]│
├─────────────────────────────────────────────────────────────┤
│ [Search Models] [Sync All Models] [View Sync History]       │
├─────────────────────────────────────────────────────────────┤
│ Model Name        Last Sync      Status    Records  Actions │
│ ──────────────────────────────────────────────────────────  │
│ 📋 Appointments   2 hrs ago      ✅ Success  1,245   [View] [Sync] │
│ 👥 Prospects      3 hrs ago      ⚠️ Partial    867   [View] [Sync] │
│ 🏢 Users          Running...     🔄 In Progress 156  [View] [Stop] │
│ 💰 Quotes         1 day ago      ❌ Failed      23   [View] [Sync] │
│ 📈 Leads          Never synced   ⏸️ Pending      0   [View] [Sync] │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
- **Model Discovery**: Introspect Django models from CRM model file
- **Sync Status**: Query `SyncHistory` for each model's latest sync
- **Status Mapping**: Map `SyncHistory.status` to UI indicators
- **Record Counts**: Query actual model tables for total record counts
- **Real-time Updates**: WebSocket/polling for running sync status updates

### **3. Sync Execution Modal**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Start Sync: genius_appointments                       [×]   │
├─────────────────────────────────────────────────────────────┤
│ Parameters:                                                 │
│ ☐ --force       Force overwrite existing records           │
│ ☐ --full        Full sync (ignore last sync timestamp)     │
│ ☐ --since       Sync since date: [2024-01-01] [📅]         │
│ ☐ --dry-run     Test mode (no database writes)             │
│                                                             │
│ Advanced Options:                                           │
│ ☐ --max-records Limit records: [1000]                      │
│ ☐ --batch-size  Batch size: [100]                          │
│ ☐ --debug       Enable verbose logging                     │
│                                                             │
│         [Cancel]                        [Start Sync]       │
└─────────────────────────────────────────────────────────────┘
```

**Functionality:**
- **Command Building**: Construct management command with selected parameters
- **Async Execution**: Run commands using Celery or subprocess
- **Real-time Progress**: WebSocket updates for sync progress
- **Command History**: Store executed commands in `SyncHistory.configuration`

### **4. Model Detail Page** (`/ingestion/crm-dashboard/{crm_source}/{model_name}/`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ genius_appointments - Detail           [Back to Models]     │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Summary ─────────────────────────────────────────────────┐ │
│ │ Total Records: 1,245    Last Sync: 2 hrs ago             │ │
│ │ Status: ✅ Success      Duration: 45 seconds              │ │
│ │ Created: 12  Updated: 133  Failed: 0                     │ │
│ │ [📊 Sync History] [⚙️ Start Sync] [🔄 Refresh]            │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Recent Sync Errors (if any) ────────────────────────────┐ │
│ │ 2024-08-12 08:30:15 - Validation error for record #123   │ │
│ │ 2024-08-12 08:28:45 - API rate limit exceeded            │ │
│ │ [View Full Error Log]                                     │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Data Table ──────────────────────────────────────────────┐ │
│ │ [Search] [Export CSV] [Show: 25 ▼] Page 1 of 50          │ │
│ │ ID    Name              Date Created    Status   Actions  │ │
│ │ ────────────────────────────────────────────────────────  │ │
│ │ 123   John Doe Apt     2024-08-12      Active   [Edit]   │ │
│ │ 124   Jane Smith Apt   2024-08-11      Pending  [Edit]   │ │
│ │ ...   ...              ...             ...      ...     │ │
│ │ ◀ Previous                                    Next ▶     │ │
│ └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
- **Summary Metrics**: Latest `SyncHistory` record for the model
- **Error Details**: Extract from `SyncHistory.error_message` and performance logs
- **Actual Data**: Query the actual Django model table with pagination
- **Dynamic Columns**: Introspect model fields to build table columns

---

## 🛠️ **Technical Implementation Plan**

### **Phase 1: Backend API Development**

#### **1.1 CRM Discovery Service**
```python
# ingestion/services/crm_discovery.py
class CRMDiscoveryService:
    def get_all_crm_sources(self) -> List[Dict]:
        """Scan ingestion/models/ for CRM model files"""
        
    def get_crm_models(self, crm_source: str) -> List[Dict]:
        """Introspect Django models from CRM model file"""
        
    def get_model_sync_status(self, crm_source: str, model_name: str) -> Dict:
        """Get latest SyncHistory for specific model"""
```

#### **1.2 Sync Management Service**
```python
# ingestion/services/sync_management.py
class SyncManagementService:
    def execute_sync_command(self, crm_source: str, model_name: str, **params) -> Dict:
        """Execute management command with parameters"""
        
    def get_sync_status(self, sync_id: int) -> Dict:
        """Get real-time sync status"""
        
    def stop_sync(self, sync_id: int) -> bool:
        """Stop running sync process"""
```

#### **1.3 Data Access Service**
```python
# ingestion/services/data_access.py
class DataAccessService:
    def get_model_data(self, model_class, page: int = 1, per_page: int = 25, search: str = None) -> Dict:
        """Get paginated model data with search"""
        
    def get_model_metadata(self, model_class) -> Dict:
        """Get model field information for table headers"""
```

### **Phase 2: API Endpoints**

#### **2.1 CRM Management APIs**
```python
# ingestion/views/crm_dashboard.py

class CRMDashboardView(TemplateView):
    """Main dashboard page"""
    template_name = 'crm_dashboard/dashboard.html'

class CRMListAPIView(APIView):
    """GET /ingestion/api/crm-dashboard/crms/"""
    def get(self, request):
        return Response(crm_discovery_service.get_all_crm_sources())

class CRMModelsAPIView(APIView):
    """GET /ingestion/api/crm-dashboard/crms/{crm_source}/models/"""
    def get(self, request, crm_source):
        return Response(crm_discovery_service.get_crm_models(crm_source))

class ModelDetailAPIView(APIView):
    """GET /ingestion/api/crm-dashboard/crms/{crm_source}/models/{model_name}/"""
    def get(self, request, crm_source, model_name):
        return Response(model_detail_data)

class ModelDataAPIView(APIView):
    """GET /ingestion/api/crm-dashboard/crms/{crm_source}/models/{model_name}/data/"""
    def get(self, request, crm_source, model_name):
        return Response(paginated_model_data)

class SyncExecuteAPIView(APIView):
    """POST /ingestion/api/crm-dashboard/sync/execute/"""
    def post(self, request):
        return Response(sync_execution_result)

class SyncStatusAPIView(APIView):
    """GET /ingestion/api/crm-dashboard/sync/{sync_id}/status/"""
    def get(self, request, sync_id):
        return Response(real_time_sync_status)
```

#### **2.2 WebSocket for Real-time Updates**
```python
# ingestion/consumers/sync_status.py
class SyncStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("sync_updates", self.channel_name)
        
    async def sync_status_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
```

### **Phase 3: Frontend Development**

#### **3.1 Dashboard Template Structure**
```
templates/crm_dashboard/
├── base.html                    # Base layout with navigation
├── dashboard.html              # Main CRM overview page
├── crm_models.html            # CRM models list page
├── model_detail.html          # Model detail page with data table
├── components/
│   ├── sync_modal.html        # Sync execution modal
│   ├── status_badge.html      # Status indicator component
│   └── data_table.html        # Reusable data table component
└── js/
    ├── dashboard.js           # Main dashboard functionality
    ├── sync_management.js     # Sync execution and monitoring
    └── real_time_updates.js   # WebSocket handling
```

#### **3.2 JavaScript Features**
```javascript
// Real-time sync status updates
class SyncStatusManager {
    constructor() {
        this.websocket = new WebSocket('ws://localhost:8000/ws/sync-status/');
        this.setupEventHandlers();
    }
    
    updateSyncStatus(data) {
        // Update UI with real-time sync progress
    }
}

// Sync command execution
class SyncCommandBuilder {
    buildCommand(crmSource, modelName, parameters) {
        // Build management command string with parameters
    }
    
    executeSync(command) {
        // Execute sync via API and monitor progress
    }
}
```

### **Phase 4: URL Configuration**

```python
# ingestion/urls.py
urlpatterns = [
    # Dashboard Pages
    path('crm-dashboard/', CRMDashboardView.as_view(), name='crm_dashboard'),
    path('crm-dashboard/<str:crm_source>/', CRMModelsView.as_view(), name='crm_models'),
    path('crm-dashboard/<str:crm_source>/<str:model_name>/', ModelDetailView.as_view(), name='model_detail'),
    
    # API Endpoints
    path('api/crm-dashboard/crms/', CRMListAPIView.as_view(), name='api_crm_list'),
    path('api/crm-dashboard/crms/<str:crm_source>/models/', CRMModelsAPIView.as_view(), name='api_crm_models'),
    path('api/crm-dashboard/crms/<str:crm_source>/models/<str:model_name>/', ModelDetailAPIView.as_view()),
    path('api/crm-dashboard/crms/<str:crm_source>/models/<str:model_name>/data/', ModelDataAPIView.as_view()),
    path('api/crm-dashboard/sync/execute/', SyncExecuteAPIView.as_view(), name='api_sync_execute'),
    path('api/crm-dashboard/sync/<int:sync_id>/status/', SyncStatusAPIView.as_view(), name='api_sync_status'),
]

# WebSocket routing
websocket_urlpatterns = [
    re_path(r'ws/sync-status/$', SyncStatusConsumer.as_asgi()),
]
```

---

## 📊 **Data Flow Architecture**

### **CRM Discovery Flow**
```
1. Scan ingestion/models/*.py files
2. Import and introspect Django models
3. Map models to management commands
4. Query SyncHistory for sync status
5. Return structured CRM data
```

### **Sync Execution Flow**
```
1. User selects model and parameters
2. Build management command string
3. Create SyncHistory record (status='running')
4. Execute command via subprocess/Celery
5. Monitor progress via WebSocket
6. Update SyncHistory on completion
7. Notify frontend of completion
```

### **Real-time Updates Flow**
```
1. Sync process starts → WebSocket broadcast
2. Progress updates → WebSocket broadcast
3. Completion/Error → WebSocket broadcast
4. Frontend updates UI automatically
```

---

## 🎨 **UI/UX Design Guidelines**

### **Color Coding for Sync Status**
- 🟢 **Success** (`success`): Green badge
- 🟡 **Partial** (`partial`): Yellow badge  
- 🔴 **Failed** (`failed`): Red badge
- 🔵 **Running** (`running`): Blue pulsing badge
- ⚪ **Never Synced**: Gray badge

### **Icons and Indicators**
- 📊 **CRM Source**: Database icon
- 📋 **Models**: Table icon
- ⚡ **Last Sync**: Lightning bolt
- 🔄 **In Progress**: Spinning icon
- ✅ **Success**: Check mark
- ⚠️ **Warning**: Triangle warning
- ❌ **Error**: X mark
- ⏸️ **Pending**: Pause icon

### **Responsive Design**
- **Desktop**: Full feature set with sidebar navigation
- **Tablet**: Collapsible cards, modal dialogs
- **Mobile**: Stacked layout, simplified actions

---

## 🧪 **Testing Strategy**

### **Unit Tests**
```python
# tests/test_crm_discovery.py
class TestCRMDiscoveryService(TestCase):
    def test_get_all_crm_sources(self):
        # Test CRM source detection
        
    def test_get_crm_models(self):
        # Test model introspection

# tests/test_sync_management.py
class TestSyncManagementService(TestCase):
    def test_execute_sync_command(self):
        # Test command execution
        
    def test_sync_status_tracking(self):
        # Test real-time status updates
```

### **Integration Tests**
```python
# tests/test_crm_dashboard_views.py
class TestCRMDashboardViews(TestCase):
    def test_dashboard_loads_all_crms(self):
        # Test main dashboard
        
    def test_model_data_pagination(self):
        # Test data table pagination
        
    def test_sync_execution_flow(self):
        # Test end-to-end sync execution
```

### **WebSocket Tests**
```python
# tests/test_sync_websockets.py
class TestSyncWebSockets(TestCase):
    def test_real_time_sync_updates(self):
        # Test WebSocket communication
```

---

## 📋 **Development Checklist**

### **Backend Development**
- [ ] Create `CRMDiscoveryService` for model introspection
- [ ] Create `SyncManagementService` for command execution
- [ ] Create `DataAccessService` for model data queries
- [ ] Implement API views for all endpoints
- [ ] Set up WebSocket consumer for real-time updates
- [ ] Add URL routing configuration
- [ ] Create management command parameter validation

### **Frontend Development**
- [ ] Create base template with navigation
- [ ] Implement main dashboard page
- [ ] Build CRM models list page
- [ ] Create model detail page with data table
- [ ] Implement sync execution modal
- [ ] Add real-time status updates via WebSocket
- [ ] Create responsive design for mobile/tablet
- [ ] Add loading states and error handling

### **Integration & Testing**
- [ ] Write unit tests for all services
- [ ] Create integration tests for API endpoints
- [ ] Test WebSocket functionality
- [ ] Perform end-to-end testing of sync execution
- [ ] Test with actual CRM data and commands
- [ ] Validate pagination and search functionality
- [ ] Test error handling and recovery

### **Documentation & Deployment**
- [ ] Update URL documentation
- [ ] Create user guide for dashboard features
- [ ] Add deployment instructions
- [ ] Update requirements.txt if needed
- [ ] Create database migration if needed

---

## 🔄 **Future Enhancements**

### **Phase 2 Features**
- **Bulk Operations**: Multi-select and bulk sync execution
- **Sync Scheduling**: Cron-like scheduling for automatic syncs
- **Data Validation**: Pre-sync data quality checks
- **Export Functionality**: CSV/Excel export of model data
- **Advanced Filtering**: Complex data table filters
- **Sync Analytics**: Performance trends and success rates

### **Phase 3 Features**
- **API Integration Testing**: Test CRM API connectivity
- **Data Mapping Visualization**: Show field mappings between CRMs
- **Conflict Resolution**: Handle sync conflicts and data merging
- **Audit Trail**: Detailed change tracking and rollback capabilities
- **Multi-tenant Support**: Separate dashboards for different environments

---

**Status**: Ready for development ✅  
**Priority**: High 🔥  
**Estimated Timeline**: 2-3 weeks  
**Dependencies**: Django, SyncHistory model, Management commands
