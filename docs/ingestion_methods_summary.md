# Data Warehouse: Data Ingestion Methods

## 📋 Overview

Our Data Warehouse platform provides **three powerful methods** for importing data from external CRM and marketing systems. Each method is designed for specific use cases and data requirements:

| Method | Best For | Setup Difficulty | Data Freshness |
|--------|----------|------------------|----------------|
| 🗂️ **CSV Import** | Historical data, one-time migrations | ⭐ Easy | Batch/Historical |
| 🔗 **Database Sync** | Real-time access to live databases | ⭐⭐ Medium | Real-time |
| 🌐 **API Sync** | Modern systems with REST APIs | ⭐⭐⭐ Advanced | Near real-time |

---

## 🗂️ Method 1: CSV Import

### 📖 What is CSV Import?

CSV Import is our **easiest and most flexible** method for bringing data into the warehouse. Simply export your data from any system as a CSV file, and our platform will intelligently map and import it.

> **💡 Perfect for:** Historical data migration, one-time imports, backup data restoration, and systems without API access.

### ⭐ Key Benefits

| Feature | Description | Business Value |
|---------|-------------|----------------|
| **🎯 Smart Field Mapping** | Automatically matches CSV headers to database fields | No manual mapping required |
| **🛡️ Data Validation** | Cleans phone numbers, emails, and dates automatically | Ensures data quality |
| **👀 Preview Mode** | Test imports without making changes | Risk-free testing |
| **📊 Progress Tracking** | Visual progress bars for large files | Monitor import status |
| **⚡ Bulk Processing** | Handles thousands of records efficiently | Fast import speeds |
| **🔄 Error Recovery** | Continues processing even with bad data | Maximizes successful imports |

### 🏢 Supported Systems

<table>
<tr><th>System</th><th>Data Types</th><th>Special Features</th></tr>
<tr><td><strong>Genius CRM</strong></td><td>Users, Appointments, Marketing Sources, Prospects</td><td>Multiple date formats supported</td></tr>
<tr><td><strong>SalesPro</strong></td><td>Appointments, Users</td><td>Sale amount tracking</td></tr>
<tr><td><strong>LeadConduit</strong></td><td>Leads</td><td>Advanced field mapping with aliases</td></tr>
<tr><td><strong>Arrivy</strong></td><td>Tasks, Activities</td><td>Location and scheduling data</td></tr>
<tr><td><strong>HubSpot</strong></td><td>Reference Data, Zip Codes</td><td>Geographic data validation</td></tr>
</table>

### 🚀 How to Use CSV Import

1. **Export your data** from the source system as a CSV file
2. **Upload the file** to our platform or specify the file path
3. **Preview the import** using dry-run mode (optional but recommended)
4. **Run the import** and monitor progress
5. **Review results** and handle any errors

### 📋 Example Commands

```bash
# Preview what will be imported (recommended first step)
python manage.py csv_leadconduit_leads /path/to/leads.csv --dry-run

# Run the actual import
python manage.py csv_leadconduit_leads /path/to/leads.csv

# Import with custom batch size for large files
BATCH_SIZE=1000 python manage.py csv_genius_users /path/to/users.csv
```

---

## 🔗 Method 2: Direct Database Sync

### 📖 What is Database Sync?

Database Sync creates a **direct, live connection** to your external system's database. This provides real-time access to the most current data without waiting for exports or API calls.

> **💡 Perfect for:** Live reporting, real-time dashboards, systems where you have database credentials, and high-frequency data updates.

### ⭐ Key Benefits

| Feature | Description | Business Value |
|---------|-------------|----------------|
| **⚡ Real-time Data** | Access live data as it changes | Always current information |
| **🔄 Incremental Sync** | Only sync changed records | Faster, more efficient |
| **🔗 Relationship Mapping** | Automatically resolves foreign keys | Complete data relationships |
| **💾 Connection Pooling** | Efficient database connections | High performance |
| **📈 Batch Processing** | Handles large datasets smoothly | Scalable for any size |
| **🛡️ Transaction Safety** | Atomic operations with rollback | Data integrity guaranteed |

### 🏢 Supported Systems

<table>
<tr><th>System</th><th>Database Type</th><th>Data Available</th></tr>
<tr><td><strong>Genius CRM</strong></td><td>MySQL</td><td>Complete database: Prospects, Appointments, Services, Quotes, Marketing Sources, Divisions, Users</td></tr>
</table>

> **⚠️ Requirements:** Database credentials and network access to the external system's database server.

### 🚀 How to Use Database Sync

1. **Configure credentials** in environment variables
2. **Test connection** to ensure access
3. **Choose sync mode** (full or incremental)
4. **Run sync command** and monitor progress
5. **Schedule regular syncs** for ongoing updates

### 🔧 Configuration Example

```bash
# Set up environment variables
export GENIUS_DB_HOST="your-db-host.com"
export GENIUS_DB_NAME="genius_production"
export GENIUS_DB_USER="warehouse_user"
export GENIUS_DB_PASSWORD="secure_password"
export GENIUS_DB_PORT="3306"
```

### 📋 Example Commands

```bash
# Sync all prospects from Genius database
python manage.py db_genius_prospects

# Sync specific table with custom batch size
python manage.py db_genius_appointments --table=appointment

# Sync all Genius data at once
python manage.py db_genius_all
```

---

## 🌐 Method 3: API Sync

### 📖 What is API Sync?

API Sync connects to external systems through their **REST APIs**, providing secure, controlled access to data with proper authentication and rate limiting. This is the most modern and flexible approach.

> **💡 Perfect for:** Cloud-based systems, modern CRMs, real-time updates via webhooks, and systems with well-documented APIs.

### ⭐ Key Benefits

| Feature | Description | Business Value |
|---------|-------------|----------------|
| **🔐 Secure Authentication** | OAuth2, API keys, JWT tokens supported | Enterprise-grade security |
| **⚡ Rate Limit Compliance** | Respects API limits automatically | Prevents service disruption |
| **📄 Pagination Handling** | Manages large datasets automatically | Complete data retrieval |
| **🔄 Incremental Updates** | Delta sync based on timestamps | Efficient data refresh |
| **🚀 Async Processing** | Non-blocking operations | High performance |
| **🔔 Webhook Support** | Real-time updates when available | Instant data synchronization |

### 🏢 Supported Systems

<table>
<tr><th>System</th><th>Authentication</th><th>Data Types</th><th>Special Features</th></tr>
<tr><td><strong>Genius CRM</strong></td><td>API Token</td><td>Users, Divisions, Prospects, Appointments, Marketing Sources</td><td>Full and incremental sync</td></tr>
<tr><td><strong>HubSpot</strong></td><td>OAuth2</td><td>Contacts, Companies, Deals, Appointments, Associations</td><td>Webhooks, complex associations</td></tr>
<tr><td><strong>ActiveProspect</strong></td><td>API Key</td><td>Events, Leads</td><td>Real-time event processing</td></tr>
<tr><td><strong>MarketSharp</strong></td><td>Basic Auth</td><td>XML/OData feeds</td><td>Custom XML processing</td></tr>
</table>

### 🚀 How to Use API Sync

1. **Configure authentication** (API keys, OAuth tokens)
2. **Choose sync type** (full or incremental)
3. **Set up scheduling** for regular updates
4. **Configure webhooks** for real-time updates (if supported)
5. **Monitor sync status** and performance

### 🔧 Authentication Setup

```bash
# Genius CRM
export GENIUS_API_TOKEN="your-api-token"
export GENIUS_BASE_URL="https://api.genius.com"

# HubSpot OAuth2
export HUBSPOT_CLIENT_ID="your-client-id"
export HUBSPOT_CLIENT_SECRET="your-client-secret"
export HUBSPOT_ACCESS_TOKEN="your-access-token"

# ActiveProspect
export ACTIVEPROSPECT_API_KEY="your-api-key"
export ACTIVEPROSPECT_BASE_URL="https://app.leadconduit.com"
```

### 📋 Example Commands

```bash
# Sync Genius users (incremental)
python manage.py sync_genius_users

# Full sync of HubSpot contacts
python manage.py sync_hubspot_contacts --full

# Sync specific date range
python manage.py sync_hubspot_contacts --lastmodifieddate=2025-01-01

# Sync with limit for testing
python manage.py sync_hubspot_appointments --limit=100

# Sync all HubSpot data
python manage.py sync_hubspot_all
```

### 🔔 Webhook Configuration

For real-time updates, configure webhooks in your source systems:

```python
# Example webhook endpoint
POST /webhooks/hubspot/contacts/
Content-Type: application/json

{
  "objectId": "12345",
  "changeType": "UPDATED",
  "timestamp": "2025-07-07T10:30:00Z"
}
```

---

## 📊 Method Comparison Guide

### 🎯 Which Method Should You Choose?

<table>
<tr><th>Scenario</th><th>Recommended Method</th><th>Why?</th></tr>
<tr><td>One-time data migration</td><td>🗂️ CSV Import</td><td>Simple, no technical setup required</td></tr>
<tr><td>Historical data analysis</td><td>🗂️ CSV Import</td><td>Export complete historical datasets</td></tr>
<tr><td>Real-time reporting</td><td>🔗 Database Sync</td><td>Live data access, no delays</td></tr>
<tr><td>Modern cloud CRM</td><td>🌐 API Sync</td><td>Native integration, webhooks available</td></tr>
<tr><td>No API available</td><td>🗂️ CSV Import</td><td>Universal compatibility</td></tr>
<tr><td>High-frequency updates</td><td>🔗 Database Sync or 🌐 API Sync</td><td>Real-time or near real-time data</td></tr>
<tr><td>Compliance requirements</td><td>🌐 API Sync</td><td>Audit trails, secure authentication</td></tr>
</table>

### ⚖️ Feature Comparison

| Feature | 🗂️ CSV Import | 🔗 Database Sync | 🌐 API Sync |
|---------|:-------------:|:---------------:|:-----------:|
| **Setup Difficulty** | ⭐ Easy | ⭐⭐ Medium | ⭐⭐⭐ Advanced |
| **Data Freshness** | Historical | Real-time | Near real-time |
| **Technical Requirements** | File access | DB credentials | API credentials |
| **Rate Limiting** | None | Connection limits | API rate limits |
| **Incremental Updates** | ❌ | ✅ | ✅ |
| **Real-time Capability** | ❌ | ✅ | ✅ (with webhooks) |
| **Performance for Large Data** | ⭐⭐⭐ High | ⭐⭐⭐ High | ⭐⭐ Medium |
| **Security** | File-based | DB authentication | API authentication |
| **Maintenance** | ⭐ Low | ⭐⭐ Medium | ⭐⭐⭐ High |

---

## 🏗️ Technical Implementation Details

### 🔄 Common Processing Pipeline

All three methods follow the same core data processing pipeline:

```
📥 Data Source → 🔍 Extraction → 🔄 Transformation → ✅ Validation → 💾 Loading → 📊 Monitoring
```

**Implementation specifics by method:**

- **🗂️ CSV**: File parsing → Field mapping → Validation → Bulk operations
- **🔗 DB Sync**: Query execution → Relationship resolution → Transformation → Bulk operations  
- **🌐 API Sync**: HTTP requests → Pagination → Rate limiting → Incremental processing

### 🛡️ Error Handling Strategy

Our platform implements a **multi-level error handling approach**:

1. **🔍 Validation Errors**: Log and skip malformed data, continue processing
2. **🔌 Connection Errors**: Retry with exponential backoff
3. **💾 Database Errors**: Transaction rollback and fallback to individual saves
4. **🌐 API Errors**: Respect rate limits, implement intelligent retry logic

### 📈 Performance Optimizations

| Optimization | CSV Import | Database Sync | API Sync |
|--------------|:----------:|:-------------:|:--------:|
| **Batch Processing** | ✅ 500-1000 records | ✅ 500-1000 records | ✅ 100-500 records |
| **Bulk Operations** | ✅ bulk_create/update | ✅ bulk_create/update | ✅ bulk_create/update |
| **Connection Pooling** | N/A | ✅ MySQL pooling | ✅ HTTP session reuse |
| **Async Processing** | ❌ Synchronous | ⚠️ Limited | ✅ Full async/await |
| **Memory Management** | ✅ File streaming | ✅ Batch processing | ✅ Chunked responses |

---

## 🎯 Getting Started

### 🚀 Quick Start Guide

1. **Choose your method** based on the comparison guide above
2. **Set up credentials** according to the method requirements
3. **Test with a small dataset** using dry-run or limit options
4. **Monitor the import process** and review results
5. **Schedule regular syncs** for ongoing data updates

### 🆘 Need Help?

- **📚 Documentation**: Check the specific command documentation for detailed usage
- **🧪 Testing**: Always use dry-run mode for CSV imports or limits for API syncs
- **📊 Monitoring**: Review sync history and error logs in the admin interface
- **🔧 Troubleshooting**: Check environment variables and network connectivity

### 📞 Support Contacts

- **Technical Issues**: Contact the Data Engineering team
- **Business Questions**: Reach out to the Data Analytics team  
- **Access Requests**: Submit tickets to IT Security
