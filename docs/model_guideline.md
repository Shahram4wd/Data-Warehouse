# Django Model Consistency Guidelines

## 🧱 1. Model Naming Convention
- Use `CamelCase` for class names, prefixed with system source (e.g., `Hubspot_Contact`, `LeadConduit_Event`, `MarketSharp_Activity`).
- Keep names singular (e.g., `SalesRabbit_Lead` instead of `SalesRabbit_Leads`) to follow Django convention.

## 🏷 2. Primary Key Definition
- Use **explicit primary keys**:
  - For external IDs: `CharField(max_length=X, primary_key=True)`
  - For UUIDs: `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
  - For Auto-incrementing: `AutoField(primary_key=True)`
- Maintain consistent use across similar models within the same system (e.g., all MarketSharp models use UUIDs where appropriate).

## 📦 3. Meta Class Consistency
Every model should have:
```python
class Meta:
    verbose_name = "Singular Form"
    verbose_name_plural = "Plural Form"
    db_table = 'explicit_table_name'
```
- Define `ordering` where useful (e.g., by `-created_at` or `-start_timestamp`).
- Add `indexes` where needed for performance on frequently queried fields (e.g., `email`, `lead_id`, `created_at`).

## 🗃 4. Field Options Standardization

| Attribute         | Guideline                                                                 |
|------------------|---------------------------------------------------------------------------|
| `null` vs `blank`| Use both (`null=True, blank=True`) for optional fields in forms and DB.   |
| `default`        | Use `default=` for Boolean or fixed-value fields (e.g., `default=False`). |
| `choices`        | Use for enums (e.g., `import_source`) to enforce validation.              |
| `max_length`     | Always specify on `CharField`, even if the field is nullable.             |

## 🧾 5. Audit & Tracking Fields
Use these standard audit fields across all models:
```python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```
For sync-specific tracking:
```python
synced_at = models.DateTimeField(auto_now=True)
```

## 🔗 6. Relationships & Foreign Keys
- Use `on_delete=models.SET_NULL` if the child can exist without the parent.
- Always add `related_name=` for reverse lookups (e.g., `'appointments'` for a prospect).
- Avoid ambiguous related names like `'division'`; be explicit: `'division_users'`.

## 🔍 7. __str__() Method
Ensure all models implement:
```python
def __str__(self):
    return "<human-readable description>"
```
Use combinations of identifying fields:
- e.g., `f"{self.first_name} {self.last_name}"`, or fallback to `id`.

## 🧠 8. Properties and Helpers
Use `@property` methods like:
```python
@property
def full_name(self):
    return f"{self.first_name or ''} {self.last_name or ''}".strip()
```
Add `full_address` when address fields exist, especially for reporting.

## 📚 9. Sync History Models
Standardize fields:
- `sync_type`, `last_synced_at`, `status`, `records_processed`, `error_message`
- Use consistent naming: `SyncHistory`, not `Sync_History`.

Example:
```python
class Meta:
    ordering = ['-last_synced_at']
    verbose_name = 'X Sync History'
    verbose_name_plural = 'X Sync Histories'
```

## 🗂 10. JSONField Usage
- When storing API payloads or variable structures, use:
```python
models.JSONField(null=True, blank=True)
```
- Avoid overuse; only use for non-relational/unstructured data.

## ✅ 11. Boolean Fields
Always use explicit defaults:
```python
models.BooleanField(default=False)
```

## ✏️ 12. Verbose Field Naming
Avoid abbreviations in class fields unless they're standard:
- Prefer `email_address` over `email1`, unless following API schema.

If multiple emails/phones exist, be consistent:
- `email_primary`, `email_secondary` (not `email1`, `email2`)

## Example Mini Template
```python
class ExampleModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_example_model'
        verbose_name = 'Example'
        verbose_name_plural = 'Examples'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name or str(self.id)
```
