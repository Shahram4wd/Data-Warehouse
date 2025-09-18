/**
 * Enhanced Dashboard Manager for CRM Dashboard
 * Handles dashboard interactions, data visualization, and advanced features
 */
class EnhancedDashboardManager {
    constructor() {
        this.refreshInterval = 30000; // 30 seconds
        this.refreshTimer = null;
        this.charts = new Map();
        this.filters = {
            search: '',
            status: 'all',
            timeRange: '24h'
        };
        this.isAutoRefreshEnabled = true;
        
        this.initializeDashboard();
        this.setupEventHandlers();
        this.startAutoRefresh();
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
            this.showLoadingState();
            
            const [crmsData, syncHistory, runningSync] = await Promise.all([
                this.fetchCRMsData(),
                this.fetchSyncHistory(),
                this.fetchRunningSyncs()
            ]);
            
            this.renderCRMCards(crmsData);
            this.renderSyncStatistics(syncHistory);
            this.renderActiveSyncs(runningSyncs);
            this.updateLastRefreshTime();
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showErrorState(error.message);
        } finally {
            this.hideLoadingState();
        }
    }
    
    async fetchCRMsData() {
        const response = await fetch('/ingestion/crm-dashboard/api/crms/');
        if (!response.ok) throw new Error('Failed to fetch CRM data');
        return await response.json();
    }
    
    async fetchSyncHistory() {
        const response = await fetch(`/ingestion/crm-dashboard/api/sync/history/?limit=100&time_range=${this.filters.timeRange}`);
        if (!response.ok) throw new Error('Failed to fetch sync history');
        return await response.json();
    }
    
    async fetchRunningSyncs() {
        const response = await fetch('/ingestion/crm-dashboard/api/sync/running/');
        if (!response.ok) throw new Error('Failed to fetch running syncs');
        return await response.json();
    }
    
    renderCRMCards(crmsData) {
        const container = document.getElementById('crm-cards-container');
        if (!container) return;
        
        // Apply search filter
        const filteredCRMs = this.applyFilters(crmsData);
        
        container.innerHTML = '';
        
        if (filteredCRMs.length === 0) {
            container.innerHTML = this.createNoResultsMessage();
            return;
        }
        
        filteredCRMs.forEach(crm => {
            const cardElement = this.createCRMCard(crm);
            container.appendChild(cardElement);
        });
        
        // Add animation to cards
        this.animateCards();
    }
    
    createCRMCard(crm) {
        const card = document.createElement('div');
        card.className = 'col-lg-4 col-md-6 mb-4 crm-card-col';
        card.setAttribute('data-crm-source', crm.source);
        
        const statusClass = this.getStatusClass(crm.overall_status);
        const statusIcon = this.getStatusIcon(crm.overall_status);
        
        card.innerHTML = `
            <div class="card crm-card h-100 shadow-sm hover-shadow">
                <div class="card-header bg-gradient-primary text-white d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <i class="fas ${this.getCRMIcon(crm.source)} fa-lg me-2"></i>
                        <h5 class="mb-0">${crm.display_name}</h5>
                    </div>
                    <span class="badge ${statusClass}">
                        <i class="fas ${statusIcon} me-1"></i>
                        ${crm.overall_status}
                    </span>
                </div>
                <div class="card-body">
                    <div class="row text-center mb-3">
                        <div class="col-4">
                            <div class="metric-box">
                                <h3 class="text-primary mb-1" data-crm-models-count="${crm.source}">${crm.model_count}</h3>
                                <small class="text-muted">Models</small>
                            </div>
                        </div>
                        <div class="col-4">
                            <div class="metric-box">
                                <h3 class="text-success mb-1" data-crm-records-count="${crm.source}">${this.formatNumber(crm.total_records)}</h3>
                                <small class="text-muted">Records</small>
                            </div>
                        </div>
                        <div class="col-4">
                            <div class="metric-box">
                                <h3 class="text-info mb-1">${crm.sync_count_24h || 0}</h3>
                                <small class="text-muted">Syncs (24h)</small>
                            </div>
                        </div>
                    </div>
                    
                    <div class="sync-info mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <small class="text-muted">Last Sync</small>
                            <small class="text-muted" data-crm-last-sync="${crm.source}">
                                ${crm.last_sync ? this.formatTimeAgo(new Date(crm.last_sync)) : 'Never'}
                            </small>
                        </div>
                        ${crm.last_sync_error ? `
                            <div class="alert alert-warning alert-sm py-2 mb-0">
                                <i class="fas fa-exclamation-triangle me-1"></i>
                                <small>${crm.last_sync_error}</small>
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="model-preview mb-3">
                        <h6 class="text-muted mb-2">Recent Models</h6>
                        <div class="model-list">
                            ${crm.models.slice(0, 3).map(model => `
                                <div class="model-item d-flex justify-content-between align-items-center py-1">
                                    <span class="model-name">${model.display_name}</span>
                                    <span class="badge bg-light text-dark">${this.formatNumber(model.record_count)}</span>
                                </div>
                            `).join('')}
                            ${crm.models.length > 3 ? `
                                <div class="text-center mt-2">
                                    <small class="text-muted">+${crm.models.length - 3} more models</small>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div class="card-footer bg-transparent">
                    <div class="row">
                        <div class="col-6">
                            <a href="/ingestion/crm-dashboard/${crm.source}/" class="btn btn-outline-primary btn-sm w-100">
                                <i class="fas fa-list me-1"></i>View Models
                            </a>
                        </div>
                        <div class="col-6">
                            <button class="btn btn-primary btn-sm w-100" onclick="window.dashboardManager.quickSync('${crm.source}')">
                                <i class="fas fa-sync me-1"></i>Quick Sync
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    renderSyncStatistics(syncHistory) {
        this.renderSyncChart(syncHistory);
        this.renderSyncMetrics(syncHistory);
        this.renderRecentActivity(syncHistory);
    }
    
    renderSyncChart(syncHistory) {
        const chartContainer = document.getElementById('sync-chart-container');
        if (!chartContainer) return;
        
        // Prepare data for chart
        const chartData = this.prepareSyncChartData(syncHistory);
        
        // Create or update chart
        if (this.charts.has('syncTrends')) {
            this.updateChart('syncTrends', chartData);
        } else {
            this.createSyncTrendsChart(chartContainer, chartData);
        }
    }
    
    prepareSyncChartData(syncHistory) {
        const now = new Date();
        const timeRange = this.filters.timeRange;
        let intervalMs, labelFormat;
        
        switch (timeRange) {
            case '1h':
                intervalMs = 5 * 60 * 1000; // 5 minutes
                labelFormat = 'HH:mm';
                break;
            case '24h':
                intervalMs = 60 * 60 * 1000; // 1 hour
                labelFormat = 'HH:mm';
                break;
            case '7d':
                intervalMs = 24 * 60 * 60 * 1000; // 1 day
                labelFormat = 'MM/dd';
                break;
            default:
                intervalMs = 60 * 60 * 1000;
                labelFormat = 'HH:mm';
        }
        
        const intervals = this.generateTimeIntervals(now, timeRange, intervalMs);
        const successData = [];
        const errorData = [];
        const labels = [];
        
        intervals.forEach(interval => {
            const syncsInInterval = syncHistory.filter(sync => {
                const syncTime = new Date(sync.started_at);
                return syncTime >= interval.start && syncTime < interval.end;
            });
            
            const successCount = syncsInInterval.filter(sync => sync.status === 'success').length;
            const errorCount = syncsInInterval.filter(sync => sync.status === 'error').length;
            
            successData.push(successCount);
            errorData.push(errorCount);
            labels.push(this.formatTime(interval.start, labelFormat));
        });
        
        return { labels, successData, errorData };
    }
    
    createSyncTrendsChart(container, data) {
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Successful Syncs',
                        data: data.successData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1,
                        fill: true
                    },
                    {
                        label: 'Failed Syncs',
                        data: data.errorData,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Sync Activity Over Time'
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
        
        this.charts.set('syncTrends', chart);
    }
    
    renderSyncMetrics(syncHistory) {
        const metricsContainer = document.getElementById('sync-metrics-container');
        if (!metricsContainer) return;
        
        const metrics = this.calculateSyncMetrics(syncHistory);
        
        metricsContainer.innerHTML = `
            <div class="row">
                <div class="col-md-3 mb-3">
                    <div class="metric-card bg-primary text-white">
                        <div class="metric-icon">
                            <i class="fas fa-sync"></i>
                        </div>
                        <div class="metric-content">
                            <h3>${metrics.totalSyncs}</h3>
                            <p class="mb-0">Total Syncs</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="metric-card bg-success text-white">
                        <div class="metric-icon">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <div class="metric-content">
                            <h3>${metrics.successRate}%</h3>
                            <p class="mb-0">Success Rate</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="metric-card bg-info text-white">
                        <div class="metric-icon">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div class="metric-content">
                            <h3>${metrics.avgDuration}s</h3>
                            <p class="mb-0">Avg Duration</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="metric-card bg-warning text-white">
                        <div class="metric-icon">
                            <i class="fas fa-database"></i>
                        </div>
                        <div class="metric-content">
                            <h3>${this.formatNumber(metrics.recordsProcessed)}</h3>
                            <p class="mb-0">Records Processed</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    calculateSyncMetrics(syncHistory) {
        const now = new Date();
        const timeRangeMs = this.getTimeRangeMs(this.filters.timeRange);
        const cutoffTime = new Date(now.getTime() - timeRangeMs);
        
        const recentSyncs = syncHistory.filter(sync => 
            new Date(sync.started_at) >= cutoffTime
        );
        
        const totalSyncs = recentSyncs.length;
        const successfulSyncs = recentSyncs.filter(sync => sync.status === 'success').length;
        const successRate = totalSyncs > 0 ? Math.round((successfulSyncs / totalSyncs) * 100) : 0;
        
        const completedSyncs = recentSyncs.filter(sync => sync.duration);
        const totalDuration = completedSyncs.reduce((sum, sync) => sum + (sync.duration || 0), 0);
        const avgDuration = completedSyncs.length > 0 ? Math.round(totalDuration / completedSyncs.length) : 0;
        
        const recordsProcessed = recentSyncs.reduce((sum, sync) => sum + (sync.records_processed || 0), 0);
        
        return { totalSyncs, successRate, avgDuration, recordsProcessed };
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
        return crmsData.filter(crm => {
            // Search filter
            if (this.filters.search) {
                const searchTerm = this.filters.search;
                if (!crm.display_name.toLowerCase().includes(searchTerm) &&
                    !crm.source.toLowerCase().includes(searchTerm)) {
                    return false;
                }
            }
            
            // Status filter
            if (this.filters.status !== 'all' && crm.overall_status !== this.filters.status) {
                return false;
            }
            
            return true;
        });
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
    
    // Auto-refresh functionality
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
    
    updateAutoRefreshUI() {
        const toggleBtn = document.getElementById('auto-refresh-toggle');
        if (toggleBtn) {
            if (this.isAutoRefreshEnabled) {
                toggleBtn.innerHTML = '<i class="fas fa-pause me-2"></i>Pause Auto-refresh';
                toggleBtn.className = 'btn btn-outline-warning btn-sm';
            } else {
                toggleBtn.innerHTML = '<i class="fas fa-play me-2"></i>Resume Auto-refresh';
                toggleBtn.className = 'btn btn-outline-success btn-sm';
            }
        }
    }
    
    // Keyboard shortcuts
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + R: Refresh dashboard
            if ((e.ctrlKey || e.metaKey) && e.key === 'r' && !e.shiftKey) {
                e.preventDefault();
                this.loadDashboardData();
            }
            
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
    getCRMIcon(source) {
        const iconMap = {
            'genius': 'fa-brain',
            'hubspot': 'fa-hubspot',
            'salesforce': 'fa-salesforce',
            'pipedrive': 'fa-pipe',
            'zoho': 'fa-z',
            'leadconduit': 'fa-funnel-dollar',
            'callrail': 'fa-phone',
            'arrivy': 'fa-truck',
            'salesrabbit': 'fa-rabbit',
            'gsheet': 'fa-table'
        };
        return iconMap[source.toLowerCase()] || 'fa-database';
    }
    
    getStatusClass(status) {
        const classMap = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'warning': 'bg-warning',
            'running': 'bg-primary',
            'pending': 'bg-secondary'
        };
        return classMap[status] || 'bg-secondary';
    }
    
    getStatusIcon(status) {
        const iconMap = {
            'success': 'fa-check-circle',
            'error': 'fa-times-circle',
            'warning': 'fa-exclamation-triangle',
            'running': 'fa-spinner fa-spin',
            'pending': 'fa-clock'
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
        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('click', () => {
                this.toggleAutoRefresh();
            });
        }
        
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
            crm.display_name,
            crm.model_count,
            crm.total_records,
            crm.last_sync || 'Never',
            crm.overall_status
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
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new EnhancedDashboardManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboardManager) {
        window.dashboardManager.destroy();
    }
});
