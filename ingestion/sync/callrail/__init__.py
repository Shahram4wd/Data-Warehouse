"""CallRail CRM sync module following the CRM sync guide architecture"""

# Import base classes
from .engines.base import CallRailBaseSyncEngine
from .processors.base import CallRailBaseProcessor

# Import entity-specific engines
from .engines.accounts import AccountsSyncEngine
from .engines.companies import CompaniesSyncEngine
from .engines.calls import CallsSyncEngine
from .engines.trackers import TrackersSyncEngine
from .engines.form_submissions import FormSubmissionsSyncEngine
from .engines.text_messages import TextMessagesSyncEngine
from .engines.tags import TagsSyncEngine
from .engines.users import UsersSyncEngine

# Import clients
from .clients.base import CallRailBaseClient
from .clients.accounts import AccountsClient
from .clients.calls import CallsClient
from .clients.companies import CompaniesClient
from .clients.trackers import TrackersClient
from .clients.form_submissions import FormSubmissionsClient
from .clients.text_messages import TextMessagesClient
from .clients.tags import TagsClient
from .clients.users import UsersClient

# Import processors
from .processors.accounts import AccountsProcessor
from .processors.calls import CallsProcessor
from .processors.companies import CompaniesProcessor
from .processors.trackers import TrackersProcessor
from .processors.form_submissions import FormSubmissionsProcessor
from .processors.text_messages import TextMessagesProcessor
from .processors.tags import TagsProcessor
from .processors.users import UsersProcessor

# Import validators
from .validators import CallRailValidator

__all__ = [
    'CallRailBaseSyncEngine',
    'CallRailBaseProcessor', 
    'CallRailBaseClient',
    # Engines
    'AccountsSyncEngine',
    'CompaniesSyncEngine',
    'CallsSyncEngine',
    'TrackersSyncEngine',
    'FormSubmissionsSyncEngine',
    'TextMessagesSyncEngine',
    'TagsSyncEngine',
    'UsersSyncEngine',
    # Clients
    'AccountsClient',
    'CallsClient',
    'CompaniesClient',
    'TrackersClient',
    'FormSubmissionsClient',
    'TextMessagesClient',
    'TagsClient',
    'UsersClient',
    # Processors
    'AccountsProcessor',
    'CallsProcessor',
    'CompaniesProcessor',
    'TrackersProcessor',
    'FormSubmissionsProcessor',
    'TextMessagesProcessor',
    'TagsProcessor',
    'UsersProcessor',
    # Validators
    'CallRailValidator',
]
