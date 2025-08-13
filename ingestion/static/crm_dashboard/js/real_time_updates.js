/**
 * Real-time Updates for CRM Dashboard
 * Handles WebSocket connections and live UI updates
 */
class RealTimeUpdatesManager {
    constructor() {
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000;
        this.isConnected = false;
        this.eventHandlers = new Map();
        this.pollingStarted = false;
        this.connectionAttempted = false;
        
        this.initializeWebSocket();
        this.setupEventHandlers();
    }
    
    connect() {
        // Prevent multiple connection attempts
        if (this.connectionAttempted) {
            return;
        }
        this.connectionAttempted = true;
        
        // Public method to start connection
        this.initializeWebSocket();
    }
    
    disconnect() {
        // Public method to disconnect
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        this.isConnected = false;
        this.connectionAttempted = false; // Allow reconnection
        this.updateConnectionStatus(false);
    }
    
    setupEventHandlers() {
        // Setup any DOM event handlers
        const connectionIndicator = document.getElementById('connection-status');
        if (connectionIndicator) {
            connectionIndicator.addEventListener('click', () => {
                if (!this.isConnected) {
                    this.connect();
                }
            });
        }
    }
    
    initializeWebSocket() {
        // Prevent multiple WebSocket initialization attempts
        if (this.websocket || this.connectionAttempted) {
            return;
        }
        this.connectionAttempted = true;
        
        // Skip WebSocket entirely since server is not configured for it
        // Go directly to polling mode for reliable updates
        this.fallbackToPolling();
        return;
        
        // Legacy WebSocket code (commented out until server is configured)
        /*
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/sync-status/`;
            
            this.websocket = new WebSocket(wsUrl);
            this.setupWebSocketHandlers();
        } catch (error) {
            this.fallbackToPolling();
        }
        */
    }
    
    setupWebSocketHandlers() {
        this.websocket.onopen = (event) => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleRealTimeUpdate(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.websocket.onclose = (event) => {
            // Silently handle close - expected when no WebSocket server
            this.isConnected = false;
            this.updateConnectionStatus(false);
            
            // Skip reconnect attempts, go straight to polling
            if (this.reconnectAttempts === 0) {
                this.fallbackToPolling();
            }
        };
        
        this.websocket.onerror = (error) => {
            // Silently handle errors - expected when no WebSocket server
            this.updateConnectionStatus(false);
        };
    }
    
    attemptReconnect() {
        // Skip reconnection attempts and go straight to polling
        // since we know WebSocket server is not available
        if (this.reconnectAttempts === 0) {
            this.fallbackToPolling();
        }
    }
    
    fallbackToPolling() {
        // Prevent multiple polling intervals
        if (this.pollingStarted) return;
        
        // Use polling mode - single info message
        console.info('Real-time updates: Using polling mode');
        this.pollingStarted = true;
        
        // Poll for updates every 10 seconds when WebSocket is unavailable
        setInterval(() => {
            this.pollForUpdates();
        }, 10000);
    }
    
    async pollForUpdates() {
        try {
            const response = await fetch('/ingestion/crm-dashboard/api/sync/running/');
            if (response.ok) {
                const result = await response.json();
                
                // Handle wrapped response format
                let data = [];
                if (result.success && Array.isArray(result.data)) {
                    data = result.data;
                } else if (Array.isArray(result)) {
                    data = result;
                } else {
                    console.warn('Unexpected polling response format:', result);
                    return;
                }
                
                this.handleSyncStatusUpdate(data);
            }
        } catch (error) {
            console.error('Error polling for updates:', error);
        }
    }
    
    handleSyncStatusUpdate(data) {
        // Handle sync status updates from polling
        if (Array.isArray(data)) {
            // Update running syncs display
            this.updateRunningSyncsDisplay(data);
            
            // Notify dashboard manager if available
            if (window.dashboardManager && typeof window.dashboardManager.updateRunningSyncs === 'function') {
                window.dashboardManager.updateRunningSyncs(data);
            }
        }
    }
    
    updateRunningSyncsDisplay(runningSyncs) {
        // Update the running syncs count in the UI
        const runningCountElement = document.querySelector('.running-syncs-count');
        if (runningCountElement) {
            runningCountElement.textContent = runningSyncs.length;
        }
        
        // Update active syncs container
        const activeSyncsContainer = document.getElementById('active-syncs-container');
        if (activeSyncsContainer && runningSyncs.length > 0) {
            activeSyncsContainer.innerHTML = runningSyncs.map(sync => `
                <div class="d-flex align-items-center mb-2">
                    <span class="badge bg-info me-2">${sync.crm_source}</span>
                    <span class="small">${sync.sync_type} - ${sync.elapsed_seconds || 0}s</span>
                    <button class="btn btn-sm btn-outline-danger ms-auto sync-action-btn" data-action="stop" data-sync-id="${sync.id}">
                        <i class="fas fa-stop"></i>
                    </button>
                </div>
            `).join('');
        } else if (activeSyncsContainer) {
            activeSyncsContainer.innerHTML = '<div class="text-muted">No active syncs</div>';
        }
    }
    
    handleRealTimeUpdate(data) {
        const { type, payload } = data;
        
        switch (type) {
            case 'sync_started':
                this.handleSyncStarted(payload);
                break;
            case 'sync_progress':
                this.handleSyncProgress(payload);
                break;
            case 'sync_completed':
                this.handleSyncCompleted(payload);
                break;
            case 'sync_error':
                this.handleSyncError(payload);
                break;
            case 'data_updated':
                this.handleDataUpdated(payload);
                break;
            default:
                console.log('Unknown update type:', type);
        }
    }
    
    handleSyncStarted(payload) {
        const { sync_id, crm_source, model_name, command } = payload;
        
        // Update UI to show sync is running
        this.updateSyncStatus(sync_id, 'running');
        this.addSyncNotification(`Started sync for ${crm_source}.${model_name}`, 'info');
        
        // Trigger custom event
        this.triggerEvent('syncStarted', payload);
    }
    
    handleSyncProgress(payload) {
        const { sync_id, progress, message } = payload;
        
        // Update progress bars
        this.updateSyncProgress(sync_id, progress, message);
        
        // Trigger custom event
        this.triggerEvent('syncProgress', payload);
    }
    
    handleSyncCompleted(payload) {
        const { sync_id, crm_source, model_name, status, records_processed } = payload;
        
        // Update UI to show completion
        this.updateSyncStatus(sync_id, status);
        this.removeSyncProgress(sync_id);
        
        const message = `Completed sync for ${crm_source}.${model_name} (${records_processed} records)`;
        this.addSyncNotification(message, status === 'success' ? 'success' : 'warning');
        
        // Refresh data tables if on relevant page
        this.refreshPageData(crm_source, model_name);
        
        // Trigger custom event
        this.triggerEvent('syncCompleted', payload);
    }
    
    handleSyncError(payload) {
        const { sync_id, crm_source, model_name, error } = payload;
        
        // Update UI to show error
        this.updateSyncStatus(sync_id, 'error');
        this.removeSyncProgress(sync_id);
        
        const message = `Error in sync for ${crm_source}.${model_name}: ${error}`;
        this.addSyncNotification(message, 'error');
        
        // Trigger custom event
        this.triggerEvent('syncError', payload);
    }
    
    handleDataUpdated(payload) {
        const { crm_source, model_name, record_count } = payload;
        
        // Update record counts in UI
        this.updateRecordCount(crm_source, model_name, record_count);
        
        // Refresh current page if viewing this model
        if (this.isCurrentModel(crm_source, model_name)) {
            this.refreshCurrentTable();
        }
        
        // Trigger custom event
        this.triggerEvent('dataUpdated', payload);
    }
    
    updateSyncStatus(syncId, status) {
        const statusElements = document.querySelectorAll(`[data-sync-id="${syncId}"]`);
        statusElements.forEach(element => {
            const badge = element.querySelector('.status-badge');
            if (badge) {
                badge.className = `badge status-badge status-${status}`;
                badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            }
        });
    }
    
    updateSyncProgress(syncId, progress, message) {
        const progressElements = document.querySelectorAll(`[data-sync-id="${syncId}"] .progress-bar`);
        progressElements.forEach(progressBar => {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            
            const progressText = progressBar.parentElement.querySelector('.progress-text');
            if (progressText) {
                progressText.textContent = message || `${progress}% complete`;
            }
        });
    }
    
    removeSyncProgress(syncId) {
        const progressElements = document.querySelectorAll(`[data-sync-id="${syncId}"] .progress-container`);
        progressElements.forEach(element => {
            element.style.display = 'none';
        });
    }
    
    addSyncNotification(message, type) {
        const notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) return;
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${this.getBootstrapAlertClass(type)} alert-dismissible fade show`;
        notification.innerHTML = `
            <i class="fas ${this.getNotificationIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        notificationContainer.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    getBootstrapAlertClass(type) {
        const mapping = {
            'info': 'info',
            'success': 'success',
            'warning': 'warning',
            'error': 'danger'
        };
        return mapping[type] || 'secondary';
    }
    
    getNotificationIcon(type) {
        const mapping = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle'
        };
        return mapping[type] || 'fa-bell';
    }
    
    updateRecordCount(crmSource, modelName, recordCount) {
        const selectors = [
            `[data-crm="${crmSource}"][data-model="${modelName}"] .record-count`,
            `[data-crm-source="${crmSource}"][data-model-name="${modelName}"] .record-count`
        ];
        
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.textContent = recordCount.toLocaleString();
            });
        });
    }
    
    isCurrentModel(crmSource, modelName) {
        const currentPath = window.location.pathname;
        return currentPath.includes(`/${crmSource}/`) && currentPath.includes(`/${modelName}/`);
    }
    
    refreshCurrentTable() {
        // Trigger table refresh if data table is present
        if (window.dataTableManager) {
            window.dataTableManager.refreshData();
        }
    }
    
    refreshPageData(crmSource, modelName) {
        // Refresh dashboard cards if on dashboard page
        if (window.location.pathname.includes('/crm-dashboard/')) {
            if (window.dashboardManager) {
                window.dashboardManager.refreshCRMCard(crmSource);
            }
        }
        
        // Refresh model list if on models page
        if (window.location.pathname.includes(`/${crmSource}/`)) {
            if (window.modelsPageManager) {
                window.modelsPageManager.refreshModelCard(modelName);
            }
        }
    }
    
    updateConnectionStatus(isConnected) {
        const statusElements = document.querySelectorAll('.realtime-status');
        statusElements.forEach(element => {
            if (isConnected) {
                element.className = 'realtime-status connected';
                element.innerHTML = '<i class="fas fa-circle text-success"></i> Live';
            } else {
                element.className = 'realtime-status disconnected';
                element.innerHTML = '<i class="fas fa-circle text-warning"></i> Polling';
            }
        });
    }
    
    // Event system for custom handlers
    on(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        this.eventHandlers.get(eventType).push(handler);
    }
    
    off(eventType, handler) {
        if (this.eventHandlers.has(eventType)) {
            const handlers = this.eventHandlers.get(eventType);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    triggerEvent(eventType, data) {
        if (this.eventHandlers.has(eventType)) {
            this.eventHandlers.get(eventType).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${eventType}:`, error);
                }
            });
        }
    }
    
    setupEventHandlers() {
        // Page visibility API - pause/resume connections when tab is hidden/visible
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Tab is hidden, reduce update frequency
                this.pauseUpdates();
            } else {
                // Tab is visible, resume normal updates
                this.resumeUpdates();
            }
        });
        
        // Connection recovery on page focus
        window.addEventListener('focus', () => {
            if (!this.isConnected) {
                this.initializeWebSocket();
            }
        });
    }
    
    pauseUpdates() {
        // Implement reduced update frequency for hidden tabs
        this.updateFrequency = 'reduced';
    }
    
    resumeUpdates() {
        // Resume normal update frequency
        this.updateFrequency = 'normal';
        
        // Refresh data when tab becomes visible
        this.refreshPageData();
    }
    
    // Cleanup method
    destroy() {
        if (this.websocket) {
            this.websocket.close();
        }
        this.eventHandlers.clear();
    }
}

// Export the class for use in templates  
window.RealTimeUpdatesManager = RealTimeUpdatesManager;
