/**
 * Enhanced Sync Management for CRM Dashboard
 * Handles complex sync operations, parameter validation, and batch processing
 */
class AdvancedSyncManager {
    constructor() {
        this.activeSyncs = new Map();
        this.syncQueue = [];
    this.maxConcurrentSyncs = 2;
        this.syncHistory = [];
        this.parameterSchemas = new Map();
        
        this.initializeManager();
        this.loadParameterSchemas();
        this.setupEventHandlers();
    }
    
    initializeManager() {
        // Load existing running syncs
        this.loadRunningSyncs();
        
        // Setup periodic status checks
        setInterval(() => {
            this.checkSyncStatuses();
        }, 5000);
        
        // Setup auto-cleanup of completed syncs
        setInterval(() => {
            this.cleanupCompletedSyncs();
        }, 30000);
    }
    
    async loadRunningSyncs() {
        try {
            const response = await fetch('/ingestion/crm-dashboard/api/sync/running/');
            if (response.ok) {
                const result = await response.json();
                
                // Handle wrapped response format
                let runningSyncs = [];
                if (result.success && Array.isArray(result.data)) {
                    runningSyncs = result.data;
                } else if (Array.isArray(result)) {
                    runningSyncs = result;
                } else {
                    console.warn('Unexpected running syncs format:', result);
                    return;
                }
                
                runningSyncs.forEach(sync => {
                    this.activeSyncs.set(sync.id, sync);
                });
                this.updateUI();
            }
        } catch (error) {
            console.error('Error loading running syncs:', error);
        }
    }
    
    async loadParameterSchemas() {
        // Load parameter schemas for different sync commands
        try {
            const response = await fetch('/ingestion/crm-dashboard/api/sync/schemas/');
            if (response.ok) {
                const result = await response.json();
                const schemas = result.success ? result.data : result;
                if (Array.isArray(schemas)) {
                    schemas.forEach(schema => {
                        this.parameterSchemas.set(schema.command, schema);
                    });
                }
            } else if (response.status === 404) {
                // Silently use defaults when endpoint not available
                this.loadDefaultSchemas();
            }
        } catch (error) {
            // Silently fall back to defaults
            this.loadDefaultSchemas();
        }
    }
    
    loadDefaultSchemas() {
        // Default parameter schemas for common commands
        const defaultSchemas = {
            'sync_hubspot_all': {
                parameters: [
                    { name: 'force', type: 'boolean', description: 'Force full sync ignoring last sync time' },
                    { name: 'skip-associations', type: 'boolean', description: 'Skip association syncing' },
                    { name: 'batch-size', type: 'number', default: 100, min: 1, max: 1000, description: 'Batch size for processing' }
                ]
            },
            'sync_genius_all': {
                parameters: [
                    { name: 'force', type: 'boolean', description: 'Force full sync' },
                    { name: 'full', type: 'boolean', description: 'Perform full sync' },
                    { name: 'since', type: 'datetime', description: 'Sync records since this date' }
                ]
            },
            'sync_gsheet_marketing_spends': {
                parameters: [
                    { name: 'force', type: 'boolean', description: 'Force update of existing records' },
                    { name: 'sheet-id', type: 'string', description: 'Specific Google Sheet ID to sync' }
                ]
            }
        };
        
        Object.entries(defaultSchemas).forEach(([command, schema]) => {
            this.parameterSchemas.set(command, schema);
        });
    }
    
    // Enhanced sync execution with validation and queuing
    async executeSync(crmSource, modelName, command, parameters = {}) {
        try {
            // Validate parameters
            const validation = this.validateParameters(command, parameters);
            if (!validation.isValid) {
                throw new Error(`Parameter validation failed: ${validation.errors.join(', ')}`);
            }
            
            // Check concurrent sync limits
            if (this.activeSyncs.size >= this.maxConcurrentSyncs) {
                return this.queueSync(crmSource, modelName, command, parameters);
            }
            
            // Show confirmation for destructive operations
            if (this.isDestructiveOperation(command, parameters)) {
                const confirmed = await this.confirmDestructiveOperation(command, parameters);
                if (!confirmed) {
                    return { status: 'cancelled', message: 'Operation cancelled by user' };
                }
            }
            
            // Execute the sync
            const syncResult = await this.performSync(crmSource, modelName, command, parameters);
            
            // Track the sync
            this.activeSyncs.set(syncResult.sync_id, {
                id: syncResult.sync_id,
                crm_source: crmSource,
                model_name: modelName,
                command: command,
                parameters: parameters,
                started_at: new Date(),
                status: 'running'
            });
            
            this.updateUI();
            return syncResult;
            
        } catch (error) {
            console.error('Sync execution error:', error);
            this.showError(`Failed to execute sync: ${error.message}`);
            throw error;
        }
    }
    
    validateParameters(command, parameters) {
        const schema = this.parameterSchemas.get(command);
        if (!schema) {
            return { isValid: true, errors: [] }; // No schema, assume valid
        }
        
        const errors = [];
        
        schema.parameters.forEach(param => {
            const value = parameters[param.name];
            
            // Check required parameters
            if (param.required && (value === undefined || value === null || value === '')) {
                errors.push(`Parameter '${param.name}' is required`);
                return;
            }
            
            // Skip validation if parameter is not provided and not required
            if (value === undefined || value === null || value === '') {
                return;
            }
            
            // Type validation
            switch (param.type) {
                case 'number':
                    if (isNaN(value)) {
                        errors.push(`Parameter '${param.name}' must be a number`);
                    } else {
                        const numValue = Number(value);
                        if (param.min !== undefined && numValue < param.min) {
                            errors.push(`Parameter '${param.name}' must be at least ${param.min}`);
                        }
                        if (param.max !== undefined && numValue > param.max) {
                            errors.push(`Parameter '${param.name}' must be at most ${param.max}`);
                        }
                    }
                    break;
                    
                case 'boolean':
                    if (typeof value !== 'boolean' && value !== 'true' && value !== 'false') {
                        errors.push(`Parameter '${param.name}' must be true or false`);
                    }
                    break;
                    
                case 'datetime':
                    if (!this.isValidDateTime(value)) {
                        errors.push(`Parameter '${param.name}' must be a valid date and time`);
                    }
                    break;
                    
                case 'string':
                    if (param.pattern && !new RegExp(param.pattern).test(value)) {
                        errors.push(`Parameter '${param.name}' format is invalid`);
                    }
                    if (param.minLength && value.length < param.minLength) {
                        errors.push(`Parameter '${param.name}' must be at least ${param.minLength} characters`);
                    }
                    if (param.maxLength && value.length > param.maxLength) {
                        errors.push(`Parameter '${param.name}' must be at most ${param.maxLength} characters`);
                    }
                    break;
            }
        });
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }
    
    isValidDateTime(value) {
        const date = new Date(value);
        return date instanceof Date && !isNaN(date);
    }
    
    isDestructiveOperation(command, parameters) {
        // Define destructive operations that need confirmation
        const destructiveCommands = ['sync_all', 'reset_sync', 'delete_records'];
        const destructiveParams = ['force', 'full', 'reset'];
        
        if (destructiveCommands.some(cmd => command.includes(cmd))) {
            return true;
        }
        
        return destructiveParams.some(param => parameters[param] === true);
    }
    
    async confirmDestructiveOperation(command, parameters) {
        return new Promise((resolve) => {
            const modal = this.createConfirmationModal(command, parameters);
            document.body.appendChild(modal);
            
            const confirmBtn = modal.querySelector('.btn-confirm');
            const cancelBtn = modal.querySelector('.btn-cancel');
            
            confirmBtn.addEventListener('click', () => {
                modal.remove();
                resolve(true);
            });
            
            cancelBtn.addEventListener('click', () => {
                modal.remove();
                resolve(false);
            });
            
            // Show the modal
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        });
    }
    
    createConfirmationModal(command, parameters) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Confirm Destructive Operation
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p><strong>Command:</strong> ${command}</p>
                        <p><strong>Parameters:</strong></p>
                        <ul>
                            ${Object.entries(parameters).map(([key, value]) => 
                                `<li><code>${key}</code>: ${value}</li>`
                            ).join('')}
                        </ul>
                        <div class="alert alert-warning">
                            <i class="fas fa-warning me-2"></i>
                            This operation may modify or replace existing data. Are you sure you want to continue?
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-cancel">Cancel</button>
                        <button type="button" class="btn btn-warning btn-confirm">
                            <i class="fas fa-check me-2"></i>Confirm
                        </button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }
    
    async performSync(crmSource, modelName, command, parameters) {
        const response = await fetch('/ingestion/crm-dashboard/api/sync/execute/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                crm_source: crmSource,
                model_name: modelName,
                command: command,
                parameters: parameters
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Sync execution failed');
        }
        
        return await response.json();
    }
    
    async queueSync(crmSource, modelName, command, parameters) {
        const queuedSync = {
            id: Date.now(), // Temporary ID
            crm_source: crmSource,
            model_name: modelName,
            command: command,
            parameters: parameters,
            queued_at: new Date(),
            status: 'queued'
        };
        
        this.syncQueue.push(queuedSync);
        this.updateUI();
        
        this.showInfo(`Sync queued: ${crmSource}.${modelName} (${this.syncQueue.length} in queue)`);
        
        return { status: 'queued', message: 'Sync added to queue', queue_position: this.syncQueue.length };
    }
    
    async processQueue() {
        if (this.syncQueue.length === 0 || this.activeSyncs.size >= this.maxConcurrentSyncs) {
            return;
        }
        
        const nextSync = this.syncQueue.shift();
        try {
            await this.executeSync(
                nextSync.crm_source,
                nextSync.model_name,
                nextSync.command,
                nextSync.parameters
            );
        } catch (error) {
            console.error('Error processing queued sync:', error);
        }
        
        this.updateUI();
    }
    
    async stopSync(syncId) {
        try {
            const response = await fetch(`/ingestion/crm-dashboard/api/sync/${syncId}/stop/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const sync = this.activeSyncs.get(syncId);
                if (sync) {
                    sync.status = 'stopped';
                    this.showInfo(`Stopped sync: ${sync.crm_source}.${sync.model_name}`);
                }
                this.updateUI();
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('Error stopping sync:', error);
            return false;
        }
    }
    
    async checkSyncStatuses() {
        const syncIds = Array.from(this.activeSyncs.keys());
        
        for (const syncId of syncIds) {
            try {
                const response = await fetch(`/ingestion/crm-dashboard/api/sync/${syncId}/status/`);
                if (response.ok) {
                    const status = await response.json();
                    this.updateSyncStatus(syncId, status);
                }
            } catch (error) {
                console.error(`Error checking status for sync ${syncId}:`, error);
            }
        }
    }
    
    updateSyncStatus(syncId, statusData) {
        const sync = this.activeSyncs.get(syncId);
        if (!sync) return;
        
        sync.status = statusData.status;
        sync.progress = statusData.progress;
        sync.message = statusData.message;
        sync.records_processed = statusData.records_processed;
        sync.error = statusData.error;
        
        if (['completed', 'error', 'stopped'].includes(statusData.status)) {
            sync.completed_at = new Date();
            
            // Move to history after a delay
            setTimeout(() => {
                this.moveToHistory(syncId);
            }, 5000);
        }
        
        this.updateUI();
    }
    
    moveToHistory(syncId) {
        const sync = this.activeSyncs.get(syncId);
        if (sync) {
            this.syncHistory.unshift(sync);
            this.activeSyncs.delete(syncId);
            
            // Keep only last 50 in memory
            if (this.syncHistory.length > 50) {
                this.syncHistory = this.syncHistory.slice(0, 50);
            }
            
            this.updateUI();
            
            // Process next in queue
            this.processQueue();
        }
    }
    
    cleanupCompletedSyncs() {
        const now = new Date();
        const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
        
        Array.from(this.activeSyncs.entries()).forEach(([syncId, sync]) => {
            if (sync.completed_at && sync.completed_at < fiveMinutesAgo) {
                this.moveToHistory(syncId);
            }
        });
    }
    
    // Batch operations
    async executeBatchSync(syncOperations) {
        const results = [];
        
        for (const operation of syncOperations) {
            try {
                const result = await this.executeSync(
                    operation.crm_source,
                    operation.model_name,
                    operation.command,
                    operation.parameters
                );
                results.push({ ...operation, result, status: 'success' });
            } catch (error) {
                results.push({ ...operation, error: error.message, status: 'error' });
            }
        }
        
        return results;
    }
    
    // UI update methods
    updateUI() {
        this.updateActiveSyncsDisplay();
        this.updateQueueDisplay();
        this.updateSyncCounters();
    }
    
    updateActiveSyncsDisplay() {
        const container = document.getElementById('active-syncs-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.activeSyncs.size === 0) {
            container.innerHTML = '<div class="text-muted">No active syncs</div>';
            return;
        }
        
        Array.from(this.activeSyncs.values()).forEach(sync => {
            const syncElement = this.createSyncElement(sync);
            container.appendChild(syncElement);
        });
    }
    
    createSyncElement(sync) {
        const element = document.createElement('div');
        element.className = 'sync-item card mb-2';
        element.setAttribute('data-sync-id', sync.id);
        
        const progressHtml = sync.progress !== undefined ? `
            <div class="progress mb-2">
                <div class="progress-bar" style="width: ${sync.progress}%" 
                     aria-valuenow="${sync.progress}" aria-valuemin="0" aria-valuemax="100">
                    ${sync.progress}%
                </div>
            </div>
        ` : '';
        
        element.innerHTML = `
            <div class="card-body p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${sync.crm_source}.${sync.model_name}</h6>
                        <small class="text-muted">${sync.command}</small>
                        ${sync.message ? `<div class="small text-info mt-1">${sync.message}</div>` : ''}
                    </div>
                    <div class="text-end">
                        <span class="badge status-badge status-${sync.status}">${sync.status}</span>
                        <button class="btn btn-sm btn-outline-danger ms-2" onclick="window.syncManager.stopSync(${sync.id})">
                            <i class="fas fa-stop"></i>
                        </button>
                    </div>
                </div>
                ${progressHtml}
                ${sync.records_processed ? `<div class="small text-muted">Processed: ${sync.records_processed.toLocaleString()} records</div>` : ''}
            </div>
        `;
        
        return element;
    }
    
    updateQueueDisplay() {
        const container = document.getElementById('sync-queue-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.syncQueue.length === 0) {
            container.innerHTML = '<div class="text-muted">No queued syncs</div>';
            return;
        }
        
        this.syncQueue.forEach((sync, index) => {
            const queueElement = this.createQueueElement(sync, index + 1);
            container.appendChild(queueElement);
        });
    }
    
    createQueueElement(sync, position) {
        const element = document.createElement('div');
        element.className = 'queue-item d-flex justify-content-between align-items-center p-2 border-bottom';
        
        element.innerHTML = `
            <div>
                <span class="badge bg-secondary me-2">#${position}</span>
                <strong>${sync.crm_source}.${sync.model_name}</strong>
                <small class="text-muted ms-2">${sync.command}</small>
            </div>
            <div>
                <small class="text-muted">${this.formatTimeAgo(sync.queued_at)}</small>
                <button class="btn btn-sm btn-outline-danger ms-2" onclick="window.syncManager.removeFromQueue(${sync.id})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        return element;
    }
    
    updateSyncCounters() {
        const activeCount = this.activeSyncs.size;
        const queueCount = this.syncQueue.length;
        
        // Update counter badges
        document.querySelectorAll('.active-syncs-count').forEach(el => {
            el.textContent = activeCount;
            el.className = `badge ${activeCount > 0 ? 'bg-primary' : 'bg-secondary'} active-syncs-count`;
        });
        
        document.querySelectorAll('.queued-syncs-count').forEach(el => {
            el.textContent = queueCount;
            el.className = `badge ${queueCount > 0 ? 'bg-warning' : 'bg-secondary'} queued-syncs-count`;
        });
    }
    
    removeFromQueue(syncId) {
        const index = this.syncQueue.findIndex(sync => sync.id === syncId);
        if (index !== -1) {
            this.syncQueue.splice(index, 1);
            this.updateUI();
        }
    }
    
    // Utility methods
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
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
    
    showInfo(message) {
        this.showNotification(message, 'info');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        if (window.realTimeUpdates) {
            window.realTimeUpdates.addSyncNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    setupEventHandlers() {
        // Listen for real-time updates
        if (window.realTimeUpdates) {
            window.realTimeUpdates.on('syncStarted', (data) => {
                // Handle sync started event
            });
            
            window.realTimeUpdates.on('syncCompleted', (data) => {
                // Handle sync completed event
            });
            
            window.realTimeUpdates.on('syncError', (data) => {
                // Handle sync error event
            });
        }
    }
}

// Export the class for use in templates - alias for template compatibility
window.SyncManager = AdvancedSyncManager;
window.AdvancedSyncManager = AdvancedSyncManager;
