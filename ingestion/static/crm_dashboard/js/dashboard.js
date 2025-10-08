/**
 * Enhanced Dashboard Manager for CRM Dashboard
 * Handles dashboard interactions, data visualization, and advanced features
 */
class EnhancedDashboardManager {
    constructor(options = {}) {
        this.refreshInterval = options.autoRefreshInterval || 30000; // 30 seconds
        this.refreshTimer = null;
        this.charts = new Map();
        this.filters = {
            search: '',
            status: 'all',
            timeRange: '24h'
        };
        this.chartContainers = options.chartContainers || {};
        this.apiEndpoints = options.apiEndpoints || {};
        // Auto-refresh disabled by default (manual refresh only)
        this.isAutoRefreshEnabled = false;
        
        try {
            this.initializeDashboard();
            this.setupEventHandlers();
        } catch (error) {
            console.error('Dashboard initialization error:', error);
        }
        // No auto-start of refresh; user uses Refresh button
    }
    
    initializeDashboard() {
        this.loadDashboardData();
        this.setupSearch();
        this.setupFilters();
        this.setupCharts();
        this.setupKeyboardShortcuts();
    }
    
    async loadDashboardData() {
        try {
            console.log('🔄 Loading dashboard data...');
            this.showLoadingState();
            
            // Load CRM list quickly without record counts
            console.log('📡 Fetching CRM data...');
            const crmsData = await this.fetchCRMsData();
            console.log('✅ CRM data received:', crmsData);
            this.renderCRMCards(crmsData);
            
            // Load other data in parallel
            console.log('📡 Fetching sync history and running syncs...');
            const [syncHistory, runningSyncs] = await Promise.all([
                this.fetchSyncHistory(),
                this.fetchRunningSyncs()
            ]);
            
            this.renderSyncStatistics(syncHistory);
            this.renderActiveSyncs(runningSyncs);
            this.updateLastRefreshTime();
            
            // Now lazy load record counts for each CRM
            console.log('🚀 Starting lazy load for record counts...');
            this.lazyLoadRecordCounts(crmsData);
            
        } catch (error) {
            console.error('❌ Error loading dashboard data:', error);
            this.showErrorState(error.message);
        } finally {
            this.hideLoadingState();
        }
    }
    
    async fetchCRMsData() {
        const response = await fetch('/ingestion/crm-dashboard/api/crms/');
        if (!response.ok) throw new Error('Failed to fetch CRM data');
        const result = await response.json();
        
        // Handle wrapped response format with crm_sources
        if (result.success && Array.isArray(result.crm_sources)) {
            return result.crm_sources;
        }
        
        // Handle wrapped response format with data (backwards compatibility)
        if (result.success && Array.isArray(result.data)) {
            return result.data;
        }
        
        // Handle direct array response
        if (Array.isArray(result)) {
            return result;
        }
        
        console.warn('Unexpected CRM data format:', result);
        return [];
    }

    async fetchSyncHistory() {
        const response = await fetch(`/ingestion/crm-dashboard/api/sync/history/?limit=100&time_range=${this.filters.timeRange}`);
        if (!response.ok) throw new Error('Failed to fetch sync history');
        const result = await response.json();
        
        // Handle wrapped response format
        if (result.success && Array.isArray(result.data)) {
            return result.data;
        }
        
        // Handle direct array response
        if (Array.isArray(result)) {
            return result;
        }
        
        console.warn('Unexpected sync history format:', result);
        return [];
    }

    async fetchRunningSyncs() {
        const response = await fetch('/ingestion/crm-dashboard/api/sync/running/');
        if (!response.ok) throw new Error('Failed to fetch running syncs');
        const result = await response.json();
        
        // Handle wrapped response format
        if (result.success && Array.isArray(result.data)) {
            return result.data;
        }
        
        // Handle direct array response
        if (Array.isArray(result)) {
            return result;
        }
        
        console.warn('Unexpected running syncs format:', result);
        return [];
    }    setupCharts() {
        // Initialize Chart.js charts if containers exist
        const syncChartContainer = document.getElementById('syncChart');
        const performanceChartContainer = document.getElementById('performanceChart');
        
        if (syncChartContainer) {
            this.initializeSyncChart(syncChartContainer);
        }
        
        if (performanceChartContainer) {
            this.initializePerformanceChart(performanceChartContainer);
        }
    }
    
    setupSearch() {
        const searchInput = document.getElementById('searchCRM');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filters.search = e.target.value.toLowerCase();
                this.renderCRMCards(this.lastCRMData || []);
            });
        }
    }
    
    setupFilters() {
        // Setup filter dropdowns and controls
        const statusFilter = document.getElementById('statusFilter');
        const timeRangeFilter = document.getElementById('timeRangeFilter');
        
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.filters.status = e.target.value;
                this.renderCRMCards(this.lastCRMData || []);
            });
        }
        
        if (timeRangeFilter) {
            timeRangeFilter.addEventListener('change', (e) => {
                this.filters.timeRange = e.target.value;
                this.loadDashboardData();
            });
        }
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+/ for search focus
            if (e.ctrlKey && e.key === '/') {
                e.preventDefault();
                const searchInput = document.getElementById('searchCRM');
                if (searchInput) {
                    searchInput.focus();
                }
            }
        });
    }
    
    renderCRMCards(crmsData) {
        console.log('🎨 Rendering CRM cards...', crmsData);
        const container = document.getElementById('crm-cards-container');
        if (!container) {
            console.error('❌ CRM cards container not found!');
            return;
        }
        
        // Ensure crmsData is an array
        if (!Array.isArray(crmsData)) {
            console.warn('⚠️ CRM data is not an array:', crmsData);
            crmsData = [];
        }
        
        console.log(`📊 Processing ${crmsData.length} CRM sources`);
        
        // Store the data for future filtering
        this.lastCRMData = crmsData;
        
        // Apply search filter
        const filteredCRMs = this.applyFilters(crmsData);
        console.log(`🔍 After filtering: ${filteredCRMs.length} CRM sources`);
        
        container.innerHTML = '';
        
        if (filteredCRMs.length === 0) {
            console.log('📭 No CRMs to display, showing no results message');
            container.innerHTML = this.createNoResultsMessage();
            return;
        }
        
        filteredCRMs.forEach((crm, index) => {
            console.log(`🔧 Creating card ${index + 1} for CRM:`, crm.name || crm.source);
            const cardElement = this.createCRMCard(crm);
            if (cardElement) {
                container.appendChild(cardElement);
                console.log(`✅ Added card for ${crm.name || crm.source}`);
            } else {
                console.error(`❌ Failed to create card for CRM:`, crm);
            }
        });
        
        console.log(`🎉 Rendered ${filteredCRMs.length} CRM cards successfully`);
        
        // Add animation to cards
        this.animateCards();
    }
    
    createCRMCard(crm) {
        // Validate CRM data
        if (!crm || typeof crm !== 'object') {
            console.warn('Invalid CRM data provided to createCRMCard');
            return null;
        }
        
        // Provide defaults for missing properties
        const crmData = {
            // API returns: name, display_name, status, last_sync (object), total_records
            source: crm.name || crm.source || 'unknown',
            display_name: crm.display_name || 'Unknown CRM',
            overall_status: crm.status || crm.overall_status || 'unknown',
            model_count: crm.model_count || 0,
            total_records: crm.total_records ?? crm.record_count ?? 0,
            last_sync: crm.last_sync || null,
            ...crm
        };
        
        const card = document.createElement('div');
        card.className = 'col-lg-4 col-md-6 mb-4 crm-card-col';
        card.setAttribute('data-crm-source', crmData.source);
        
    const statusClass = this.getStatusClass(crmData.overall_status);
    const statusIcon = this.getStatusIcon(crmData.overall_status);
        
        card.innerHTML = `
            <div class="card crm-card h-100 shadow-sm hover-shadow">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <i class="${this.getCRMIconClass(crmData.source)} fa-lg me-2"></i>
                        <h5 class="mb-0">${crmData.display_name}</h5>
                    </div>
                    <span class="badge ${statusClass}">
                        <i class="fas ${statusIcon} me-1"></i>
                        ${crmData.overall_status}
                    </span>
                </div>
                <div class="card-body">
                    <div class="row text-center mb-3">
                        <div class="col-6">
                            <div class="metric-box">
                                <h3 class="text-primary mb-1" data-crm-models-count="${crmData.source}">${crmData.model_count}</h3>
                                <small class="text-muted">Models</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="metric-box">
                                <h3 class="text-success mb-1" data-crm-records-count="${crmData.source}">
                                    <i class="fas fa-spinner fa-spin text-muted"></i>
                                </h3>
                                <small class="text-muted">Records</small>
                            </div>
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">Last Sync</small>
                        <small class="text-muted" data-crm-last-sync="${crmData.source}">
                            ${crmData.last_sync ? (crmData.last_sync.time_ago || (crmData.last_sync.start_time ? this.formatTimeAgo(new Date(crmData.last_sync.start_time)) : 'Never')) : 'Never'}
                        </small>
                    </div>
                </div>
                <div class="card-footer bg-transparent">
                    <div class="row">
                        <div class="col-6">
                            <a href="/ingestion/crm-dashboard/${crmData.source}/" class="btn btn-outline-primary btn-sm w-100">
                                <i class="fas fa-list me-1"></i>View Models
                            </a>
                        </div>
                        <div class="col-6">
                            <button class="btn btn-primary btn-sm w-100" onclick="window.dashboardManager.quickSync('${crmData.source}')">
                                <i class="fas fa-sync me-1"></i>Sync All
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    renderSyncStatistics(syncHistory) {
        this.renderRecentActivity(syncHistory);
    }
    
    renderRecentActivity(syncHistory) {
        const activityContainer = document.getElementById('recent-activity-container');
        if (!activityContainer) return;
        
        const recentSyncs = syncHistory.slice(0, 10);
        
        activityContainer.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Recent Activity</h6>
                    <a href="/ingestion/crm-dashboard/history/" class="btn btn-sm btn-outline-primary">View All</a>
                </div>
                <div class="card-body p-0">
                    <div class="activity-list">
                        ${recentSyncs.map(sync => this.createActivityItem(sync)).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    createActivityItem(sync) {
        const statusIcon = this.getStatusIcon(sync.status);
        const statusClass = this.getStatusClass(sync.status);
        
        return `
            <div class="activity-item d-flex align-items-center p-3 border-bottom">
                <div class="activity-icon me-3">
                    <i class="fas ${statusIcon} text-${this.getStatusColor(sync.status)}"></i>
                </div>
                <div class="activity-content flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>${sync.crm_source}.${sync.model_name}</strong>
                            <small class="text-muted d-block">${sync.command}</small>
                        </div>
                        <div class="text-end">
                            <span class="badge ${statusClass}">${sync.status}</span>
                            <small class="text-muted d-block">${this.formatTimeAgo(new Date(sync.started_at))}</small>
                        </div>
                    </div>
                    ${sync.records_processed ? `
                        <small class="text-muted">Processed ${this.formatNumber(sync.records_processed)} records</small>
                    ` : ''}
                    ${sync.error ? `
                        <div class="text-danger small mt-1">${sync.error}</div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    renderActiveSyncs(runningSyncs) {
        const container = document.getElementById('active-syncs-dashboard');
        if (!container) return;
        
        if (runningSyncs.length === 0) {
            container.innerHTML = `
                <div class="card">
                    <div class="card-body text-center py-4">
                        <i class="fas fa-pause-circle fa-3x text-muted mb-3"></i>
                        <h6 class="text-muted">No active syncs</h6>
                    </div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Active Syncs</h6>
                    <span class="badge bg-primary">${runningSyncs.length}</span>
                </div>
                <div class="card-body p-0">
                    ${runningSyncs.map(sync => this.createActiveSyncItem(sync)).join('')}
                </div>
            </div>
        `;
    }
    
    createActiveSyncItem(sync) {
        return `
            <div class="active-sync-item p-3 border-bottom" data-sync-id="${sync.id}">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>${sync.crm_source}.${sync.model_name}</strong>
                    <div class="d-flex align-items-center">
                        <span class="badge bg-primary me-2">Running</span>
                        <button class="btn btn-sm btn-outline-danger" onclick="window.syncManager.stopSync(${sync.id})">
                            <i class="fas fa-stop"></i>
                        </button>
                    </div>
                </div>
                ${sync.progress !== undefined ? `
                    <div class="progress mb-2">
                        <div class="progress-bar" style="width: ${sync.progress}%" 
                             aria-valuenow="${sync.progress}" aria-valuemin="0" aria-valuemax="100">
                            ${sync.progress}%
                        </div>
                    </div>
                ` : ''}
                <small class="text-muted">
                    Started ${this.formatTimeAgo(new Date(sync.started_at))}
                    ${sync.message ? ` • ${sync.message}` : ''}
                </small>
            </div>
        `;
    }
    
    // Search and filter functionality
    setupSearch() {
        const searchInput = document.getElementById('crm-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.filters.search = e.target.value.toLowerCase();
                this.loadDashboardData();
            }, 300));
        }
    }
    
    setupFilters() {
        // Status filter
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.filters.status = e.target.value;
                this.loadDashboardData();
            });
        }
        
        // Time range filter
        const timeRangeFilter = document.getElementById('time-range-filter');
        if (timeRangeFilter) {
            timeRangeFilter.addEventListener('change', (e) => {
                this.filters.timeRange = e.target.value;
                this.loadDashboardData();
            });
        }
    }
    
    applyFilters(crmsData) {
        // Ensure crmsData is an array
        if (!Array.isArray(crmsData)) {
            console.warn('applyFilters received non-array data:', crmsData);
            return [];
        }
        
        return crmsData.filter(crm => {
            // Normalize properties for consistent access
            const source = crm.name || crm.source || 'unknown';
            const displayName = crm.display_name || 'Unknown CRM';
            const status = crm.status || crm.overall_status || 'unknown';
            
            // Search filter
            if (this.filters.search) {
                const searchTerm = this.filters.search;
                if (!displayName.toLowerCase().includes(searchTerm) &&
                    !source.toLowerCase().includes(searchTerm)) {
                    return false;
                }
            }
            
            // Status filter
            if (this.filters.status !== 'all' && status !== this.filters.status) {
                return false;
            }
            
            return true;
        });
    }
    
    // Lazy loading for record counts
    async lazyLoadRecordCounts(crmsData) {
        console.log('🚀 Starting lazy load for', crmsData.length, 'CRMs');
        // Load record counts for each CRM in the background
        for (const crm of crmsData) {
            if (crm.name) {
                console.log('📊 Scheduling lazy load for:', crm.name);
                // Add a small delay to stagger requests
                setTimeout(() => this.loadRecordCountForCRM(crm.name), Math.random() * 2000);
            } else {
                console.warn('⚠️ CRM missing name property:', crm);
            }
        }
    }
    
    async loadRecordCountForCRM(crmSource) {
        try {
            console.log(`Loading record count for ${crmSource}`);
            const recordCountElement = document.querySelector(`[data-crm-records-count="${crmSource}"]`);
            if (!recordCountElement) {
                console.warn(`No element found for ${crmSource}`);
                return;
            }
            
            // Show loading state
            recordCountElement.innerHTML = '<i class="fas fa-spinner fa-spin text-primary"></i>';
            
            const response = await fetch(`/ingestion/crm-dashboard/api/crms/${crmSource}/record-count/`);
            if (!response.ok) throw new Error('Failed to fetch record count');
            
            const result = await response.json();
            console.log(`Record count for ${crmSource}:`, result);
            
            if (result.success) {
                // Update the record count with formatted number
                recordCountElement.innerHTML = this.formatNumber(result.total_records);
                console.log(`Updated ${crmSource} with ${result.total_records} records`);
            } else {
                recordCountElement.innerHTML = '-';
            }
            
        } catch (error) {
            console.error(`Error loading record count for ${crmSource}:`, error);
            const recordCountElement = document.querySelector(`[data-crm-records-count="${crmSource}"]`);
            if (recordCountElement) {
                recordCountElement.innerHTML = '<i class="fas fa-exclamation-triangle text-warning" title="Failed to load"></i>';
            }
        }
    }
    
    // Quick actions
    async quickSync(crmSource) {
        try {
            const modal = this.createQuickSyncModal(crmSource);
            document.body.appendChild(modal);
            
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
            
            // Load available commands for this CRM
            await this.loadQuickSyncCommands(crmSource, modal);
            
        } catch (error) {
            console.error('Error opening quick sync:', error);
            this.showError(`Failed to open quick sync: ${error.message}`);
        }
    }
    
    createQuickSyncModal(crmSource) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'quick-sync-modal';
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-sync me-2"></i>
                            Quick Sync - ${crmSource}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="quick-sync-loading" class="text-center py-4">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2">Loading available commands...</p>
                        </div>
                        <div id="quick-sync-content" style="display: none;">
                            <!-- Content will be loaded here -->
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="execute-quick-sync" disabled>
                            <i class="fas fa-play me-2"></i>Execute Sync
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    async loadQuickSyncCommands(crmSource, modal) {
        try {
            const response = await fetch(`/ingestion/crm-dashboard/api/crms/${crmSource}/commands/`);
            if (!response.ok) throw new Error('Failed to load commands');
            
            const commands = await response.json();
            
            const loadingDiv = modal.querySelector('#quick-sync-loading');
            const contentDiv = modal.querySelector('#quick-sync-content');
            
            loadingDiv.style.display = 'none';
            contentDiv.style.display = 'block';
            
            contentDiv.innerHTML = this.createQuickSyncForm(crmSource, commands);
            
            const executeBtn = modal.querySelector('#execute-quick-sync');
            executeBtn.disabled = false;
            
            executeBtn.addEventListener('click', () => {
                this.executeQuickSync(crmSource, modal);
            });
            
        } catch (error) {
            console.error('Error loading commands:', error);
            modal.querySelector('#quick-sync-loading').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load commands: ${error.message}
                </div>
            `;
        }
    }
    
    createQuickSyncForm(crmSource, commands) {
        return `
            <div class="quick-sync-form">
                <div class="mb-3">
                    <label class="form-label">Select Command</label>
                    <select class="form-select" id="quick-sync-command">
                        <option value="">Choose a sync command...</option>
                        ${commands.map(cmd => `
                            <option value="${cmd.command}">${cmd.display_name}</option>
                        `).join('')}
                    </select>
                </div>
                
                <div class="mb-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="quick-sync-force">
                        <label class="form-check-label" for="quick-sync-force">
                            Force sync (ignore last sync time)
                        </label>
                    </div>
                </div>
                
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    This will execute the selected command with default parameters. For advanced options, use the full sync interface.
                </div>
            </div>
        `;
    }
    
    async executeQuickSync(crmSource, modal) {
        const commandSelect = modal.querySelector('#quick-sync-command');
        const forceCheck = modal.querySelector('#quick-sync-force');
        
        if (!commandSelect.value) {
            this.showError('Please select a command');
            return;
        }
        
        const parameters = {};
        if (forceCheck.checked) {
            parameters.force = true;
        }
        
        try {
            await window.syncManager.executeSync(crmSource, 'all', commandSelect.value, parameters);
            
            bootstrap.Modal.getInstance(modal).hide();
            modal.remove();
            
            this.showSuccess(`Quick sync started for ${crmSource}`);
            
        } catch (error) {
            console.error('Quick sync error:', error);
            this.showError(`Quick sync failed: ${error.message}`);
        }
    }
    
    // Auto-refresh functionality (disabled by default; still available if toggled via code)
    startAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        if (this.isAutoRefreshEnabled) {
            this.refreshTimer = setInterval(() => {
                this.loadDashboardData();
            }, this.refreshInterval);
        }
    }
    
    toggleAutoRefresh() {
        this.isAutoRefreshEnabled = !this.isAutoRefreshEnabled;
        
        if (this.isAutoRefreshEnabled) {
            this.startAutoRefresh();
        } else {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        this.updateAutoRefreshUI();
    }
    
    updateAutoRefreshUI() { /* auto-refresh UI removed */ }
    
    // Keyboard shortcuts
    setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K: Focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.getElementById('crm-search');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Escape: Clear search
            if (e.key === 'Escape') {
                const searchInput = document.getElementById('crm-search');
                if (searchInput && searchInput === document.activeElement) {
                    searchInput.value = '';
                    this.filters.search = '';
                    this.loadDashboardData();
                }
            }
        });
    }
    
    // Animation and visual effects
    animateCards() {
        const cards = document.querySelectorAll('.crm-card-col');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }
    
    showLoadingState() {
        const container = document.getElementById('crm-cards-container');
        if (container) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-3 text-muted">Loading CRM data...</p>
                </div>
            `;
        }
    }
    
    hideLoadingState() {
        // Loading state will be replaced by actual content
    }
    
    showErrorState(message) {
        const container = document.getElementById('crm-cards-container');
        if (container) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error loading dashboard: ${message}
                        <button class="btn btn-outline-danger btn-sm ms-3" onclick="window.dashboardManager.loadDashboardData()">
                            <i class="fas fa-retry me-1"></i>Retry
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    createNoResultsMessage() {
        return `
            <div class="col-12 text-center py-5">
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No CRMs found</h5>
                <p class="text-muted">Try adjusting your search or filter criteria</p>
                <button class="btn btn-outline-primary" onclick="window.dashboardManager.clearFilters()">
                    <i class="fas fa-times me-2"></i>Clear Filters
                </button>
            </div>
        `;
    }
    
    clearFilters() {
        this.filters = {
            search: '',
            status: 'all',
            timeRange: '24h'
        };
        
        // Reset UI
        const searchInput = document.getElementById('crm-search');
        if (searchInput) searchInput.value = '';
        
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) statusFilter.value = 'all';
        
        const timeRangeFilter = document.getElementById('time-range-filter');
        if (timeRangeFilter) timeRangeFilter.value = '24h';
        
        this.loadDashboardData();
    }
    
    updateLastRefreshTime() {
        const elements = document.querySelectorAll('.last-refresh-time');
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        
        elements.forEach(el => {
            el.textContent = `Last updated: ${timeString}`;
        });
    }
    
    // Utility methods
    getCRMIconClass(source) {
        // Return full Font Awesome classes (supports brand icons)
        if (!source || typeof source !== 'string') return 'fas fa-database';
        const s = source.toLowerCase();
        const map = {
            genius: 'fas fa-brain',
            hubspot: 'fab fa-hubspot',
            callrail: 'fas fa-phone',
            arrivy: 'fas fa-truck',
            salespro: 'fas fa-briefcase',
            salesrabbit: 'fas fa-bug',
            leadconduit: 'fas fa-bolt',
            marketsharp: 'fas fa-chart-line',
            gsheet: 'fas fa-table',
            google: 'fas fa-table'
        };
        return map[s] || 'fas fa-database';
    }
    
    getStatusClass(status) {
        const classMap = {
            success: 'bg-success',
            error: 'bg-danger',
            warning: 'bg-warning',
            running: 'bg-primary',
            never_synced: 'bg-secondary',
            outdated: 'bg-warning'
        };
        return classMap[status] || 'bg-secondary';
    }
    
    getStatusIcon(status) {
        const iconMap = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            running: 'fa-spinner fa-spin',
            never_synced: 'fa-circle',
            outdated: 'fa-clock'
        };
        return iconMap[status] || 'fa-question-circle';
    }
    
    getStatusColor(status) {
        const colorMap = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'running': 'primary',
            'pending': 'secondary'
        };
        return colorMap[status] || 'secondary';
    }
    
    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return new Intl.NumberFormat().format(num);
    }
    
    formatTimeAgo(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }
    
    formatTime(date, format) {
        // Simple time formatting
        const options = {
            'HH:mm': { hour: '2-digit', minute: '2-digit' },
            'MM/dd': { month: '2-digit', day: '2-digit' }
        };
        return date.toLocaleString('en-US', options[format] || { hour: '2-digit', minute: '2-digit' });
    }
    
    generateTimeIntervals(endTime, range, intervalMs) {
        const intervals = [];
        const rangeMs = this.getTimeRangeMs(range);
        const startTime = new Date(endTime.getTime() - rangeMs);
        
        let currentTime = startTime;
        while (currentTime < endTime) {
            const nextTime = new Date(currentTime.getTime() + intervalMs);
            intervals.push({
                start: new Date(currentTime),
                end: nextTime > endTime ? endTime : nextTime
            });
            currentTime = nextTime;
        }
        
        return intervals;
    }
    
    getTimeRangeMs(range) {
        const rangeMap = {
            '1h': 60 * 60 * 1000,
            '24h': 24 * 60 * 60 * 1000,
            '7d': 7 * 24 * 60 * 60 * 1000,
            '30d': 30 * 24 * 60 * 60 * 1000
        };
        return rangeMap[range] || rangeMap['24h'];
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    showSuccess(message) {
        if (window.realTimeUpdates) {
            window.realTimeUpdates.addSyncNotification(message, 'success');
        }
    }
    
    showError(message) {
        if (window.realTimeUpdates) {
            window.realTimeUpdates.addSyncNotification(message, 'error');
        }
    }
    
    setupEventHandlers() {
    // Auto-refresh toggle removed (manual refresh only)
        
        // Manual refresh button
        const refreshBtn = document.getElementById('manual-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDashboardData();
            });
        }
        
        // Export functionality
        const exportBtn = document.getElementById('export-dashboard');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportDashboardData();
            });
        }
    }
    
    async exportDashboardData() {
        try {
            const data = await this.fetchCRMsData();
            const csvData = this.convertToCSV(data);
            this.downloadCSV(csvData, 'crm-dashboard-export.csv');
        } catch (error) {
            console.error('Export error:', error);
            this.showError('Failed to export dashboard data');
        }
    }
    
    convertToCSV(data) {
        const headers = ['CRM Source', 'Models', 'Records', 'Last Sync', 'Status'];
        const rows = data.map(crm => [
            crm.display_name || 'Unknown CRM',
            crm.model_count || 0,
            crm.total_records || crm.record_count || 0,
            crm.last_sync || 'Never',
            crm.status || crm.overall_status || 'unknown'
        ]);
        
        return [headers, ...rows]
            .map(row => row.map(field => `"${field}"`).join(','))
            .join('\n');
    }
    
    downloadCSV(csvData, filename) {
        const blob = new Blob([csvData], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }
    
    // Public API methods for external access
    refreshCRMCard(crmSource) {
        // Refresh specific CRM card data
        this.loadDashboardData();
    }
    
    // Cleanup
    destroy() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.charts.forEach(chart => {
            chart.destroy();
        });
        this.charts.clear();
    }
    
    // Methods expected by template
    refreshData() {
        return this.loadDashboardData();
    }
    
    startAutoRefresh() {
        this.isAutoRefreshEnabled = true;
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        this.refreshTimer = setInterval(() => {
            this.loadDashboardData();
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        this.isAutoRefreshEnabled = false;
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
    
    // Method for refreshing dashboard data
    refreshData() {
        this.loadDashboardData();
    }
    
    // Cleanup method called on page unload
    cleanup() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        // Cleanup charts
        this.charts.forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts.clear();
    }
}

// Export the class for use in templates
window.EnhancedDashboardManager = EnhancedDashboardManager;
