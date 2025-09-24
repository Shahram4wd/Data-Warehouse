/**
 * Worker Pool Integration for CRM Dashboard
 * 
 * This module enhances the existing sync management to work with the backend
 * worker pool system, providing proper queue management and worker limits.
 */

class WorkerPoolManager {
    constructor() {
        this.apiBaseUrl = '/ingestion/crm-dashboard/api/worker-pool/';
        this.maxWorkers = 2; // Default, will be loaded from server
        this.updateInterval = 2000; // 2 seconds
        this.statusUpdateTimer = null;
        
        // Initialize worker pool integration
        this.init();
    }
    
    async init() {
        try {
            // Load initial configuration
            await this.loadConfiguration();
            
            // Start status monitoring
            this.startStatusMonitoring();
            
            // Update UI
            this.updateUI();
            
            console.log('Worker Pool Manager initialized');
        } catch (error) {
            console.error('Failed to initialize Worker Pool Manager:', error);
        }
    }
    
    async loadConfiguration() {
        try {
            const response = await fetch(`${this.apiBaseUrl}config/`);
            if (response.ok) {
                const config = await response.json();
                if (config.success) {
                    this.maxWorkers = config.config.max_workers;
                    console.log(`Loaded worker pool config: max_workers=${this.maxWorkers}`);
                }
            }
        } catch (error) {
            console.error('Error loading worker pool configuration:', error);
        }
    }
    
    async getWorkerPoolStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}status/`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    return data.data;
                }
            }
            return null;
        } catch (error) {
            console.error('Error getting worker pool status:', error);
            return null;
        }
    }
    
    async submitSyncTask(crmSource, syncType, parameters = {}, priority = 0) {
        try {
            // Guard against undefined or falsy syncType
            const safeSyncType = syncType || parameters.sync_type || 'all';
            const response = await fetch(`${this.apiBaseUrl}submit/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    crm_source: crmSource,
                    sync_type: safeSyncType,
                    parameters: parameters,
                    priority: priority
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showNotification(
                        `Task submitted: ${crmSource}.${safeSyncType} (Status: ${result.status})`,
                        'success'
                    );
                    
                    if (result.queue_position) {
                        this.showNotification(
                            `Task queued at position ${result.queue_position}`,
                            'info'
                        );
                    }
                    
                    // Update UI immediately
                    this.updateUI();
                    
                    return result;
                } else {
                    throw new Error(result.error || 'Unknown error');
                }
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to submit task');
            }
        } catch (error) {
            this.showNotification(`Failed to submit task: ${error.message}`, 'error');
            console.error('Error submitting sync task:', error);
            throw error;
        }
    }
    
    async cancelTask(taskId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}tasks/${taskId}/cancel/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showNotification('Task cancelled successfully', 'success');
                    this.updateUI();
                    return true;
                } else {
                    throw new Error(result.error || 'Unknown error');
                }
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to cancel task');
            }
        } catch (error) {
            this.showNotification(`Failed to cancel task: ${error.message}`, 'error');
            console.error('Error cancelling task:', error);
            return false;
        }
    }
    
    async processQueue() {
        try {
            const response = await fetch(`${this.apiBaseUrl}process-queue/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showNotification('Queue processing triggered', 'info');
                    this.updateUI();
                    return result.stats;
                } else {
                    throw new Error(result.error || 'Unknown error');
                }
            }
        } catch (error) {
            this.showNotification(`Failed to process queue: ${error.message}`, 'error');
            console.error('Error processing queue:', error);
            return null;
        }
    }
    
    async updateMaxWorkers(maxWorkers) {
        try {
            const response = await fetch(`${this.apiBaseUrl}config/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    max_workers: maxWorkers
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.maxWorkers = maxWorkers;
                    this.showNotification(result.message, 'success');
                    this.updateUI();
                    return true;
                } else {
                    throw new Error(result.error || 'Unknown error');
                }
            }
        } catch (error) {
            this.showNotification(`Failed to update max workers: ${error.message}`, 'error');
            console.error('Error updating max workers:', error);
            return false;
        }
    }
    
    startStatusMonitoring() {
        // Clear any existing timer
        if (this.statusUpdateTimer) {
            clearInterval(this.statusUpdateTimer);
        }
        
        // Start new timer
        this.statusUpdateTimer = setInterval(() => {
            this.updateUI();
        }, this.updateInterval);
    }
    
    stopStatusMonitoring() {
        if (this.statusUpdateTimer) {
            clearInterval(this.statusUpdateTimer);
            this.statusUpdateTimer = null;
        }
    }
    
    async updateUI() {
        try {
            const status = await this.getWorkerPoolStatus();
            if (status) {
                // Prefer Celery real-time stats for truthy counts
                const cel = status.celery || null;
                const effective = {
                    active_count: cel && typeof cel.active === 'number' ? cel.active : status.active_count,
                    queued_count: cel && typeof cel.total_queued === 'number' ? cel.total_queued : status.queued_count,
                    max_workers: status.max_workers,
                    available_workers: status.max_workers - (cel && typeof cel.active === 'number' ? cel.active : status.active_count),
                };

                this.updateWorkerPoolDisplay({
                    ...status,
                    ...effective,
                });
                // Display active tasks: prefer Celery active task names if provided
                const activeTasks = (status.active_tasks && status.active_tasks.length)
                    ? status.active_tasks
                    : (cel && Array.isArray(cel.active_tasks)) ? cel.active_tasks.map((t, i) => ({
                        id: t.id || `celery-${i}`,
                        crm_source: (t.name || '').split('.')?.[1] || 'celery',
                        sync_type: (t.name || '').split('.')?.slice(-1)[0] || 'task',
                        started_at: null,
                        status: 'running',
                    })) : [];
                this.updateActiveSyncsDisplay(activeTasks);

                // Queue list is maintained by our worker-pool; broker depth is just a number
                this.updateQueueDisplay(status.queued_tasks || []);
                this.updateCounters({
                    active_count: effective.active_count,
                    queued_count: effective.queued_count,
                });
            }
        } catch (error) {
            console.error('Error updating UI:', error);
        }
    }
    
    updateWorkerPoolDisplay(status) {
        // Update worker pool status section
        const container = document.getElementById('worker-pool-status');
        if (container) {
            container.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span><strong>Worker Pool Status</strong></span>
                    <button class="btn btn-sm btn-outline-primary" onclick="workerPoolManager.showConfigModal()">
                        <i class="fas fa-cog"></i> Configure
                    </button>
                </div>
                <div class="row text-center">
                    <div class="col-4">
                        <div class="stat-value">${status.active_count}</div>
                        <div class="stat-label">Active</div>
                    </div>
                    <div class="col-4">
                        <div class="stat-value">${status.queued_count}</div>
                        <div class="stat-label">Queued</div>
                    </div>
                    <div class="col-4">
                        <div class="stat-value">${status.available_workers}</div>
                        <div class="stat-label">Available</div>
                    </div>
                </div>
                <div class="progress mt-2">
                    <div class="progress-bar ${status.active_count >= status.max_workers ? 'bg-warning' : 'bg-success'}" 
                         style="width: ${(status.active_count / status.max_workers) * 100}%">
                         ${status.active_count}/${status.max_workers}
                    </div>
                </div>
            `;
        }
    }
    
    updateActiveSyncsDisplay(activeTasks) {
        const container = document.getElementById('active-syncs-container');
        if (container) {
            if (activeTasks.length === 0) {
                container.innerHTML = '<div class="text-muted">No active syncs</div>';
                return;
            }
            
            container.innerHTML = activeTasks.map(task => `
                <div class="active-sync-item p-2 border-bottom" data-task-id="${task.id}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${task.crm_source}.${task.sync_type}</strong>
                            <div class="text-muted small">Started: ${this.formatTime(task.started_at)}</div>
                        </div>
                        <div class="d-flex align-items-center">
                            <span class="badge bg-primary me-2">${task.status}</span>
                            <button class="btn btn-sm btn-outline-danger" 
                                    onclick="workerPoolManager.cancelTask('${task.id}')">
                                <i class="fas fa-stop"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }
    
    updateQueueDisplay(queuedTasks) {
        const container = document.getElementById('sync-queue-container');
        if (container) {
            if (queuedTasks.length === 0) {
                container.innerHTML = '<div class="text-muted">No queued syncs</div>';
                return;
            }
            
            container.innerHTML = queuedTasks.map(task => `
                <div class="queue-item p-2 border-bottom" data-task-id="${task.id}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="badge bg-secondary me-2">#${task.position}</span>
                            <strong>${task.crm_source}.${task.sync_type}</strong>
                            ${task.priority > 0 ? `<span class="badge bg-info ms-1">Priority: ${task.priority}</span>` : ''}
                            <div class="text-muted small">Queued: ${this.formatTime(task.queued_at)}</div>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" 
                                onclick="workerPoolManager.cancelTask('${task.id}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        }
    }
    
    updateCounters(status) {
        // Update counter badges
        document.querySelectorAll('.active-syncs-count').forEach(el => {
            el.textContent = status.active_count;
            el.className = `badge ${status.active_count > 0 ? 'bg-primary' : 'bg-secondary'} active-syncs-count`;
        });
        
        document.querySelectorAll('.queued-syncs-count').forEach(el => {
            el.textContent = status.queued_count;
            el.className = `badge ${status.queued_count > 0 ? 'bg-warning' : 'bg-secondary'} queued-syncs-count`;
        });
    }
    
    showConfigModal() {
        const modalHtml = `
            <div class="modal fade" id="workerPoolConfigModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Worker Pool Configuration</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label for="maxWorkersInput" class="form-label">Maximum Workers</label>
                                <input type="number" class="form-control" id="maxWorkersInput" 
                                       value="${this.maxWorkers}" min="1" max="10">
                                <div class="form-text">Maximum number of concurrent sync workers (1-10)</div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="workerPoolManager.saveConfiguration()">
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if present
        document.querySelectorAll('#workerPoolConfigModal').forEach(el => el.remove());
        
        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('workerPoolConfigModal'));
        modal.show();
    }
    
    async saveConfiguration() {
        const maxWorkersInput = document.getElementById('maxWorkersInput');
        const newMaxWorkers = parseInt(maxWorkersInput.value);
        
        if (newMaxWorkers && newMaxWorkers >= 1 && newMaxWorkers <= 10) {
            const success = await this.updateMaxWorkers(newMaxWorkers);
            if (success) {
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('workerPoolConfigModal'));
                modal.hide();
            }
        } else {
            this.showNotification('Maximum workers must be between 1 and 10', 'error');
        }
    }
    
    // Utility methods
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    formatTime(isoString) {
        if (!isoString) return 'N/A';
        const date = new Date(isoString);
        return date.toLocaleTimeString();
    }
    
    showNotification(message, type = 'info') {
        // Use existing notification system or create simple toast
        if (window.syncManager && typeof window.syncManager.showNotification === 'function') {
            window.syncManager.showNotification(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
    
    // Integration with existing sync manager
    integrateWithSyncManager() {
        if (window.syncManager) {
            // Override the executeSync method to use worker pool
            const originalExecuteSync = window.syncManager.executeSync.bind(window.syncManager);
            
            window.syncManager.executeSync = async (...args) => {
                try {
                    // Support both forms:
                    // 1) executeSync(crmSource, modelName, command, parameters)
                    // 2) executeSync({ crm_source, sync_type, parameters })
                    if (args.length === 1 && typeof args[0] === 'object') {
                        const payload = args[0] || {};
                        const crmSource = payload.crm_source || payload.source || '';
                        const syncType = (payload.sync_type && payload.sync_type !== 'undefined') ? payload.sync_type : 'all';
                        const params = payload.parameters || {};
                        const result = await this.submitSyncTask(crmSource, syncType, params);
                        return result;
                    } else {
                        const [crmSource, modelName, command, parameters = {}] = args;
                        // Resolve syncType from modelName when possible, fallback to provided parameters or 'all'
                        let resolvedSyncType = null;
                        try {
                            if (typeof window.modelNameToSyncType === 'function') {
                                resolvedSyncType = window.modelNameToSyncType(modelName);
                            }
                        } catch (e) {
                            // ignore mapping errors, fallback below
                        }
                        if (!resolvedSyncType) {
                            resolvedSyncType = (parameters.sync_type && parameters.sync_type !== 'undefined') ? parameters.sync_type : (modelName || 'all');
                        }
                        const result = await this.submitSyncTask(crmSource, resolvedSyncType, parameters);
                        return result;
                    }
                    
                } catch (error) {
                    console.error('Worker pool sync execution failed:', error);
                    // Fallback to original method
                    return await originalExecuteSync(...args);
                }
            };
        }
    }
}

// Initialize worker pool manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.workerPoolManager = new WorkerPoolManager();
    
    // Integrate with existing sync manager after a short delay
    setTimeout(() => {
        if (window.workerPoolManager) {
            window.workerPoolManager.integrateWithSyncManager();
        }
    }, 1000);
});

// Handle page unload
window.addEventListener('beforeunload', function() {
    if (window.workerPoolManager) {
        window.workerPoolManager.stopStatusMonitoring();
    }
});

// Export for use in other scripts
window.WorkerPoolManager = WorkerPoolManager;