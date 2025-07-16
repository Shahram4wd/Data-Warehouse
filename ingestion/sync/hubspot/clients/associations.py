"""
HubSpot associations API client
Following import_refactoring.md enterprise architecture standards
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from enum import Enum
from .base import HubSpotBaseClient
from ingestion.base.exceptions import APIException, ValidationException, RateLimitException

logger = logging.getLogger(__name__)

class AssociationType(Enum):
    """Supported association types with HubSpot object mappings"""
    CONTACT_TO_APPOINTMENT = ("contacts", "0-421")  # Custom object for appointments
    CONTACT_TO_DIVISION = ("contacts", "2-37778609")  # Custom object for divisions
    APPOINTMENT_TO_CONTACT = ("0-421", "contacts")
    DIVISION_TO_CONTACT = ("2-37778609", "contacts")
    CONTACT_TO_DEAL = ("contacts", "deals")
    DEAL_TO_CONTACT = ("deals", "contacts")

class HubSpotAssociationsClient(HubSpotBaseClient):

    async def stream_all_contact_appointment_associations(self, batch_size: int = 100) -> AsyncGenerator[dict, None]:
        """
        Stream all associations from contacts to appointments, handling both batch and per-contact paging.
        Follows import_refactoring.md enterprise patterns.
        Yields flattened association records (model-compatible).
        """
        # Get all contact IDs in batches
        contact_ids = await self._get_all_contact_ids()
        total_contacts = len(contact_ids)
        for i in range(0, total_contacts, batch_size):
            batch_ids = contact_ids[i:i+batch_size]
            # For each contact in the batch, handle paging
            paging_map = {cid: None for cid in batch_ids}  # contact_id -> after cursor
            finished = set()
            while len(finished) < len(batch_ids):
                inputs = []
                for cid in batch_ids:
                    if cid in finished:
                        continue
                    after = paging_map[cid]
                    if after:
                        inputs.append({"id": cid, "after": after})
                    else:
                        inputs.append({"id": cid})
                if not inputs:
                    break
                # Call batch endpoint
                results = await self._fetch_associations_page("contacts", "0-421", [inp["id"] for inp in inputs])
                # Map from id to association result
                id_to_result = {r.get("from", {}).get("id"): r for r in results}
                for inp in inputs:
                    cid = inp["id"]
                    result = id_to_result.get(cid)
                    if not result:
                        finished.add(cid)
                        continue
                    # Flatten and yield all associations for this contact
                    flattened = self._flatten_associations([result], AssociationType.CONTACT_TO_APPOINTMENT)
                    for record in flattened:
                        yield record
                    # Check for paging
                    paging = result.get("paging", {})
                    next_after = paging.get("next", {}).get("after")
                    if next_after:
                        paging_map[cid] = next_after
                    else:
                        finished.add(cid)
    async def fetch_associations_batch(self, from_object_type: str, to_object_type: str, object_ids: list[str], flatten: bool = True) -> list[dict]:
        """
        Generic batch fetch for associations using HubSpot v4 batch API.
        Args:
            from_object_type: Source object type (e.g., 'contacts')
            to_object_type: Target object type (e.g., '0-421', '2-37778609')
            object_ids: List of source object IDs
            flatten: If True, return flattened records matching Django model; else, return raw API response
        Returns:
            List of association records (flattened or raw)
        """
        results = await self._fetch_associations_page(from_object_type, to_object_type, object_ids)
        if flatten:
            # Try to infer association type for flattening
            assoc_type = None
            for at in AssociationType:
                if at.value == (from_object_type, to_object_type):
                    assoc_type = at
                    break
            if assoc_type:
                return self._flatten_associations(results, assoc_type)
            else:
                # Fallback: return raw if association type is not supported
                return results
        else:
            return results
    """
    HubSpot API client for associations between objects
    Follows enterprise architecture standards from import_refactoring.md
    """
    
    # Batch processing limits per HubSpot API
    DEFAULT_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 100
    
    async def fetch_contact_appointment_associations(self, contact_ids: List[str], 
                                                   batch_size: Optional[int] = None,
                                                   **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch associations between contacts and appointments
        
        Args:
            contact_ids: List of contact IDs to fetch associations for
            batch_size: Batch size for processing (default: 100)
            
        Returns:
            List of association records matching Hubspot_AppointmentContactAssociation model
        """
        return await self._fetch_associations_by_type(
            AssociationType.CONTACT_TO_APPOINTMENT,
            contact_ids,
            batch_size,
            **kwargs
        )
    
    async def fetch_contact_division_associations(self, contact_ids: List[str],
                                                batch_size: Optional[int] = None,
                                                **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch associations between contacts and divisions
        
        Args:
            contact_ids: List of contact IDs to fetch associations for
            batch_size: Batch size for processing (default: 100)
            
        Returns:
            List of association records matching Hubspot_ContactDivisionAssociation model
        """
        return await self._fetch_associations_by_type(
            AssociationType.CONTACT_TO_DIVISION,
            contact_ids,
            batch_size,
            **kwargs
        )
    
    async def fetch_contact_appointment_associations_batch(self, batch_size: Optional[int] = None,
                                                         max_records: Optional[int] = None,
                                                         **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch all contact-appointment associations in batches
        
        Args:
            batch_size: Size of each batch (default: 100)
            max_records: Maximum number of records to fetch (0 for unlimited)
            
        Yields:
            Batches of association records
        """
        async for batch in self._fetch_all_associations_by_type(
            AssociationType.CONTACT_TO_APPOINTMENT,
            batch_size or self.DEFAULT_BATCH_SIZE,
            max_records or 0,
            **kwargs
        ):
            yield batch
    
    async def fetch_contact_division_associations_batch(self, batch_size: Optional[int] = None,
                                                      max_records: Optional[int] = None,
                                                      **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch all contact-division associations in batches
        
        Args:
            batch_size: Size of each batch (default: 100)
            max_records: Maximum number of records to fetch (0 for unlimited)
            
        Yields:
            Batches of association records
        """
        async for batch in self._fetch_all_associations_by_type(
            AssociationType.CONTACT_TO_DIVISION,
            batch_size or self.DEFAULT_BATCH_SIZE,
            max_records or 0,
            **kwargs
        ):
            yield batch
    
    async def _fetch_associations_by_type(self, association_type: AssociationType,
                                        object_ids: List[str],
                                        batch_size: Optional[int] = None,
                                        **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch associations for specific object IDs using HubSpot associations API
        
        Args:
            association_type: Type of association to fetch
            object_ids: List of object IDs to fetch associations for
            batch_size: Batch size for API calls (default: 100)
            
        Returns:
            List of flattened association records ready for database storage
        """
        if not object_ids:
            return []
        
        batch_size = min(batch_size or self.DEFAULT_BATCH_SIZE, self.MAX_BATCH_SIZE)
        from_object_type, to_object_type = association_type.value
        
        all_associations = []
        
        # Process object IDs in batches
        for i in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[i:i + batch_size]
            
            try:
                # Use HubSpot associations batch API
                associations = await self._fetch_associations_page(
                    from_object_type=from_object_type,
                    to_object_type=to_object_type,
                    object_ids=batch_ids
                )
                
                logger.info(f"Raw associations from API: {len(associations)} records")
                
                # Flatten associations for database storage
                flattened = self._flatten_associations(associations, association_type)
                logger.info(f"After flattening: {len(flattened)} records")
                all_associations.extend(flattened)
                
            except Exception as e:
                logger.error(f"Error fetching associations batch for {association_type.name}: {e}")
                # Continue with next batch
                continue
        
        return all_associations
    
    async def _fetch_all_associations_by_type(self, association_type: AssociationType,
                                            batch_size: int,
                                            max_records: int,
                                            **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Fetch all associations of a specific type by first getting all source object IDs
        
        Args:
            association_type: Type of association to fetch
            batch_size: Batch size for processing
            max_records: Maximum number of records to fetch (0 for unlimited)
            
        Yields:
            Batches of association records
        """
        from_object_type, to_object_type = association_type.value
        
        # Get all source object IDs based on association type
        if association_type in [AssociationType.CONTACT_TO_APPOINTMENT, AssociationType.CONTACT_TO_DIVISION]:
            source_ids = await self._get_all_contact_ids()
        elif association_type == AssociationType.APPOINTMENT_TO_CONTACT:
            source_ids = await self._get_all_appointment_ids()
        elif association_type == AssociationType.DIVISION_TO_CONTACT:
            source_ids = await self._get_all_division_ids()
        else:
            raise APIException(f"Unsupported association type: {association_type}")
        
        if not source_ids:
            logger.warning(f"No source IDs found for {association_type.name}")
            return
        
        logger.info(f"Found {len(source_ids)} source objects for {association_type.name}")
        
        records_fetched = 0
        
        # Process source IDs in batches
        for i in range(0, len(source_ids), batch_size):
            if max_records > 0 and records_fetched >= max_records:
                break
            
            batch_ids = source_ids[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_ids)} source IDs")
            
            try:
                # Process contact IDs in smaller sub-batches for association fetching
                sub_batch_size = min(10, len(batch_ids))  # Process 10 contacts at a time
                association_batch = []
                
                for j in range(0, len(batch_ids), sub_batch_size):
                    if max_records > 0 and records_fetched >= max_records:
                        break
                        
                    sub_batch_ids = batch_ids[j:j + sub_batch_size]
                    
                    # Fetch associations for this sub-batch of contacts
                    sub_associations = await self._fetch_associations_by_type(
                        association_type,
                        sub_batch_ids,
                        sub_batch_size
                    )
                    
                    logger.info(f"Sub-batch {j//sub_batch_size + 1}: got {len(sub_associations)} associations from {len(sub_batch_ids)} contacts")
                    
                    # Add to current batch
                    association_batch.extend(sub_associations)
                    
                    # Yield when we reach the desired batch size or have collected enough
                    if len(association_batch) >= batch_size or (max_records > 0 and records_fetched + len(association_batch) >= max_records):
                        # Limit to max_records if specified
                        if max_records > 0:
                            remaining = max_records - records_fetched
                            if len(association_batch) > remaining:
                                association_batch = association_batch[:remaining]
                        
                        if association_batch:
                            records_fetched += len(association_batch)
                            logger.info(f"Yielding batch with {len(association_batch)} associations (total fetched: {records_fetched})")
                            yield association_batch
                            association_batch = []  # Reset for next batch
                            
                            if max_records > 0 and records_fetched >= max_records:
                                break
                
                # Yield any remaining associations in the final batch
                if association_batch:
                    # Limit to max_records if specified
                    if max_records > 0:
                        remaining = max_records - records_fetched
                        if len(association_batch) > remaining:
                            association_batch = association_batch[:remaining]
                    
                    if association_batch:
                        records_fetched += len(association_batch)
                        logger.info(f"Yielding final batch with {len(association_batch)} associations (total fetched: {records_fetched})")
                        yield association_batch
                        
            except Exception as e:
                logger.error(f"Error fetching associations batch: {e}")
                # Continue with next batch
                continue
    
    async def _fetch_associations_page(self, from_object_type: str, to_object_type: str,
                                     object_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch a single page of associations using HubSpot batch read API
        
        Args:
            from_object_type: Source object type (e.g., 'contacts')
            to_object_type: Target object type (e.g., '0-421', '2-37778609')
            object_ids: List of source object IDs
            
        Returns:
            Raw API response with association data
        """
        try:
            # Use HubSpot associations v4 batch read endpoint
            endpoint = f"crm/v4/associations/{from_object_type}/{to_object_type}/batch/read"
            
            payload = {
                "inputs": [{"id": obj_id} for obj_id in object_ids]
            }
            
            response_data = await self.make_request("POST", endpoint, json=payload)
            results = response_data.get("results", [])
            
            logger.info(f"Fetched {len(results)} association results from {from_object_type} to {to_object_type}")
            return results
            
        except Exception as e:
            if "not found" in str(e).lower() or "no associations" in str(e).lower():
                # Expected when no associations exist
                logger.debug(f"No associations found for {from_object_type} -> {to_object_type}: {e}")
                return []
            else:
                logger.error(f"Error fetching associations {from_object_type} -> {to_object_type}: {e}")
                raise APIException(f"Failed to fetch associations: {e}")
    
    def _flatten_associations(self, associations: List[Dict[str, Any]], 
                            association_type: AssociationType) -> List[Dict[str, Any]]:
        """
        Flatten HubSpot association response to match our Django model structure
        
        Args:
            associations: Raw association response from HubSpot API
            association_type: Type of association being processed
            
        Returns:
            List of flattened association records ready for database storage
        """
        flattened = []
        logger.info(f"Flattening {len(associations)} raw associations for {association_type.name}")
        
        for association in associations:
            from_object = association.get("from", {})
            to_objects = association.get("to", [])
            
            from_id = from_object.get("id")
            if not from_id:
                logger.debug(f"Skipping association with no from_id: {association}")
                continue
            
            logger.debug(f"Processing association from {from_id} to {len(to_objects)} objects")
            
            for to_object in to_objects:
                # HubSpot API returns 'toObjectId' field, not 'id'
                to_id = to_object.get("id") or to_object.get("toObjectId")
                if not to_id:
                    logger.debug(f"Skipping to_object with no id or toObjectId: {to_object}")
                    continue
                
                # Create record based on association type
                if association_type in [AssociationType.CONTACT_TO_APPOINTMENT, AssociationType.APPOINTMENT_TO_CONTACT]:
                    # Appointment-Contact association
                    if association_type == AssociationType.CONTACT_TO_APPOINTMENT:
                        record = {
                            "contact_id": from_id,
                            "appointment_id": to_id
                        }
                    else:  # APPOINTMENT_TO_CONTACT
                        record = {
                            "contact_id": to_id,
                            "appointment_id": from_id
                        }
                elif association_type in [AssociationType.CONTACT_TO_DIVISION, AssociationType.DIVISION_TO_CONTACT]:
                    # Contact-Division association
                    if association_type == AssociationType.CONTACT_TO_DIVISION:
                        record = {
                            "contact_id": from_id,
                            "division_id": to_id
                        }
                    else:  # DIVISION_TO_CONTACT
                        record = {
                            "contact_id": to_id,
                            "division_id": from_id
                        }
                else:
                    logger.warning(f"Unsupported association type: {association_type}")
                    continue
                
                # Add metadata
                record.update({
                    "association_types": to_object.get("associationTypes", []),
                    "raw_from": from_object,
                    "raw_to": to_object
                })
                
                logger.debug(f"Created flattened record: {record}")
                flattened.append(record)
        
        logger.info(f"Flattening complete: {len(flattened)} records created")
        return flattened
    
    async def _get_all_contact_ids(self) -> List[str]:
        """Get all contact IDs from database"""
        from asgiref.sync import sync_to_async
        from ingestion.models.hubspot import Hubspot_Contact
        
        return await sync_to_async(
            lambda: list(Hubspot_Contact.objects.values_list('id', flat=True))
        )()
    
    async def _get_all_appointment_ids(self) -> List[str]:
        """Get all appointment IDs from database"""
        from asgiref.sync import sync_to_async
        from ingestion.models.hubspot import Hubspot_Appointment
        
        return await sync_to_async(
            lambda: list(Hubspot_Appointment.objects.values_list('id', flat=True))
        )()
    
    async def _get_all_division_ids(self) -> List[str]:
        """Get all division IDs from database"""
        from asgiref.sync import sync_to_async
        from ingestion.models.hubspot import Hubspot_Division
        
        return await sync_to_async(
            lambda: list(Hubspot_Division.objects.values_list('id', flat=True))
        )()
    
    # Legacy method for backward compatibility
    async def fetch_associations(self, from_object_type: str, to_object_type: str,
                               object_ids: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Legacy method for backward compatibility"""
        logger.warning("Using legacy fetch_associations method. Consider using specific type methods.")
        
        # Map to association type
        if from_object_type == "contacts" and to_object_type in ["0-421", "appointments"]:
            association_type = AssociationType.CONTACT_TO_APPOINTMENT
        elif from_object_type == "contacts" and to_object_type in ["2-37778609", "divisions"]:
            association_type = AssociationType.CONTACT_TO_DIVISION
        elif from_object_type in ["0-421", "appointments"] and to_object_type == "contacts":
            association_type = AssociationType.APPOINTMENT_TO_CONTACT
        elif from_object_type in ["2-37778609", "divisions"] and to_object_type == "contacts":
            association_type = AssociationType.DIVISION_TO_CONTACT
        else:
            raise APIException(f"Unsupported association: {from_object_type} -> {to_object_type}")
        
        return await self._fetch_associations_by_type(association_type, object_ids, **kwargs)