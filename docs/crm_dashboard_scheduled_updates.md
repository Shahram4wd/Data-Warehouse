# CRM Dashboard: Scheduled Updates Feature Requirements

## Overview
Add a feature to the detail view of each CRM dashboard item (e.g., Arrivy) to allow staff/superusers to configure, view, and manage update schedules. Scheduling is database-backed via django-celery-beat. Multiple schedules per item are supported.

## UI/UX
- Add a "Setup Update Schedule" button to the detail view of each item.
- Display a list of existing schedules for the item, showing:
  - Name
  - Type (Full/Delta)
  - Flags (same as manual run)
  - Frequency (interval or specific time)
  - Enabled/disabled status
  - Next run time
  - Last run time
  - Last status (success/failure)
  - Last error (if any)
  - "Run now" action
- Provide forms to add, edit, or delete schedules.
- Use server-rendered Django templates; minimal JS for toggles and actions.

## Schedule Configuration
- Fields:
  - Name (string)
  - Flags (same options as manual run)
  - Frequency:
    - Interval (e.g., every 5 min)
    - Specific time (e.g., daily at 2am, weekends)
  - Optional start/end date/time
  - Enabled/disabled toggle
- Allow multiple schedules per item.
- Only staff/superusers can add/edit/delete schedules.
- Changes take effect after clicking Save.

## Backend
- Use django-celery-beat for schedule storage and management.
- Link schedules to specific dashboard items/models.
- On schedule run, trigger the appropriate update task (full/delta) with selected flags.
- Store and display last run time, status, and error for each schedule.
- Implement "Run now" action to trigger the update immediately.

## Permissions
- Only staff/superusers can manage schedules.
- Non-staff users cannot view or modify schedules.

## Acceptance Criteria
- Staff/superusers can add, edit, delete, and run schedules from the item detail view.
- Multiple schedules per item are supported.
- Schedules are stored in the database and drive celery beat.
- UI displays next run, last run, last status, last error, and provides a "Run now" action.
- All changes are server-rendered; minimal JS is used for toggles and actions.
