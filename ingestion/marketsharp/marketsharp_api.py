import aiohttp
import asyncio
import hmac
import hashlib
from base64 import b64decode, b64encode
from time import time
import logging

MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds to wait before retrying after a 503 error
RECORDS_PER_PAGE = 5000

logger = logging.getLogger(__name__)

class MarketSharpAPI:
    nsmap = {
        'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
        'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
        'atom': 'http://www.w3.org/2005/Atom',
    }

    def __init__(self, company_id, api_key, secret_key, logger=None):
        if not company_id or not api_key or not secret_key:
            raise ValueError("Missing required MarketSharp credentials: company_id, api_key, or secret_key.")
        self._coi = company_id
        self._api_key = api_key
        self._secret_key = secret_key
        self._logger = logger or logging.getLogger(__name__)
        if not logger:
            logging.basicConfig(level=logging.DEBUG)

    def handle(self, *args, **kwargs):
        # Ensure the logger is properly configured
        logging.basicConfig(level=logging.INFO)

    def _get_headers(self):
        ts = int(time())
        msg = f'{self._coi}{self._api_key}{ts}'.encode('utf-8')
        secret_key_decoded = b64decode(self._secret_key)

        if not secret_key_decoded:
            raise ValueError("Invalid secret key. Ensure MARKETSHARP_SECRET_KEY is correctly set.")

        self._logger.info(f"Timestamp: {ts}, Message: {msg}, Decoded Secret Key (first 4): {secret_key_decoded[:4]}...")

        h = self._make_hash(secret_key_decoded, msg)
        auth = f'{self._coi}:{self._api_key}:{ts}:{h}'
        return {'Authorization': auth}

    def _make_hash(self, secret_key, msg):
        h = hmac.new(secret_key, msg, hashlib.sha256).digest()
        return b64encode(h).decode('utf-8')

    async def get_data(self, session, url, last_update=None, skip=0):
        headers = self._get_headers()
        if last_update:
            # Format last_update to OData compatible string
            last_update_str = f"datetime'{last_update.strftime('%Y-%m-%dT%H:%M:%S')}'"
            filter_query = f"lastUpdate gt {last_update_str}"
        else:
            filter_query = ''
        paginated_url = f"{url}?$top={RECORDS_PER_PAGE}&$skip={skip}"
        if filter_query:
            paginated_url += f"&$filter={filter_query}&$orderby=lastUpdate asc"
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                self._logger.info(f"Attempt {attempts + 1} of {MAX_RETRIES}")
                self._logger.info(f"Fetching URL: {paginated_url}")
                async with session.get(paginated_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 503:
                        self._logger.warning(f"503 Service Unavailable. Retrying after {RETRY_DELAY} seconds...")
                        await asyncio.sleep(RETRY_DELAY)
                    elif response.status in (400, 404):
                        self._logger.warning(f"{response.status}: The server encountered an error. Retrying after {RETRY_DELAY} seconds...")
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        self._logger.error(f"Error {response.status}: {await response.text()}")
                        raise Exception(f"Server error {response.status}: {await response.text()}")
            except aiohttp.ClientError as e:
                self._logger.error(f"Network error: {e}")
                raise Exception(f"Network error while fetching MarketSharp data: {e}")
            attempts += 1

        raise Exception(f"Failed to fetch data from MarketSharp after {MAX_RETRIES} attempts.")
    
    async def get_related_data(self, session, url, record_id, relation):
        related_url = f"{url}('{record_id}')/{relation}"
        headers = self._get_headers()
        async with session.get(related_url, headers=headers) as response:
            if response.status == 200:
                return await response.text()
            else:
                self._logger.error(f"Error {response.status}: {await response.text()}")
                raise Exception(f"Error fetching {relation} data for ID {record_id}")
