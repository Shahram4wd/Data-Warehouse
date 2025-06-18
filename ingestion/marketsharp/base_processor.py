from typing import List, Dict, Any, Tuple, Optional, Set
from django.db import transaction
from asgiref.sync import sync_to_async
from uuid import UUID
from datetime import datetime
from dateutil.parser import parse as parse_date
import logging
from enum import Enum
from dataclasses import dataclass
from functools import lru_cache

class FieldType(Enum):
    UUID = 'uuid'
    DATETIME = 'datetime'
    BOOLEAN = 'boolean'
    INTEGER = 'int'
    FLOAT = 'float'
    DECIMAL = 'decimal'
    STRING = 'string'

@dataclass
class ProcessingResult:
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class FieldMapping:
    xml_field: str
    model_field: str
    field_type: FieldType
    required: bool = False
    default: Any = None

    def __post_init__(self):
        if isinstance(self.field_type, str):
            self.field_type = FieldType(self.field_type)
        if self.required and self.default is not None:
            raise ValueError(f"Field {self.model_field} cannot be both required and have a default value")

class BaseProcessor:
    def __init__(self, logger: logging.Logger, data_processor):
        self.logger = logger
        self.data_processor = data_processor

    @staticmethod
    def is_valid_uuid(val: str) -> bool:
        if not val:
            return False
        try:
            UUID(val)
            return True
        except (ValueError, AttributeError):
            return False

    def parse_value(self, value: str, field_type: FieldType, field_name: str) -> Any:
        """Parse field value with enhanced type handling and validation."""
        if value is None:
            return None
            
        try:
            if field_type == FieldType.UUID:
                return UUID(value) if self.is_valid_uuid(value) else None
            elif field_type == FieldType.DATETIME:
                return parse_date(value) if value else None
            elif field_type == FieldType.BOOLEAN:
                return value.lower() == 'true' if value else False
            elif field_type == FieldType.INTEGER:
                return int(value) if value else None
            elif field_type == FieldType.FLOAT:
                return float(value) if value else None
            elif field_type == FieldType.DECIMAL:
                return float(value) if value else None
            elif field_type == FieldType.STRING:
                return value or ''
            return value
        except Exception as e:
            self.logger.warning(f"Failed to parse {field_name} ({field_type.value}): {str(e)}")
            return None

    @lru_cache(maxsize=100)
    def get_model_fields(self, model) -> Set[str]:
        """Cache model fields to improve performance."""
        return {field.name for field in model._meta.fields if not field.primary_key}

    def find_primary_key_mapping(self, field_mappings: Dict[str, FieldMapping]) -> Tuple[str, str]:
        # First check for a field mapped to 'id'
        for key, mapping in field_mappings.items():
            if mapping.model_field == 'id':
                return key, 'id'
        
        # If no 'id' mapping found, look for any UUID field as fallback
        for key, mapping in field_mappings.items():
            if mapping.field_type == FieldType.UUID:
                return key, mapping.model_field
        
        # If no UUID field found, use the first mapping as fallback
        if field_mappings:
            first_key = next(iter(field_mappings))
            first_mapping = field_mappings[first_key]
            return first_key, first_mapping.model_field
        
        # This should never happen, but provide a safe fallback
        raise ValueError("No field mappings provided")

    def extract_data(self, entry: Dict[str, Any], field_mappings: Dict[str, FieldMapping]) -> Tuple[Optional[UUID], Dict[str, Any]]:
        """Extract and validate data from a dictionary entry."""
        data = {}
        object_id = None
        has_required_fields = True
        
        # Find primary key mapping
        pk_key, pk_model_field = self.find_primary_key_mapping(field_mappings)

        for key, mapping in field_mappings.items():
            value = entry.get(mapping.xml_field)
            parsed_value = self.parse_value(value, mapping.field_type, key)

            if mapping.required and parsed_value is None:
                self.logger.error(f"Missing required field: {key}")
                has_required_fields = False
                continue

            data[mapping.model_field] = parsed_value if parsed_value is not None else mapping.default

            # Use the identified primary key field
            if key == pk_key:
                object_id = parsed_value

        return (object_id, data) if has_required_fields else (None, {})

    async def process_entries(
        self,
        entries: List[Dict[str, Any]],
        model,
        field_mappings: Dict[str, FieldMapping],
        batch_size: int
    ) -> int:
        """Process entries with enhanced error handling and metrics."""
        result = ProcessingResult(
            total_processed=len(entries),
            successful=0,
            failed=0,
            errors=[]
        )

        try:
            valid_records: List[Tuple[UUID, Dict[str, Any]]] = []
            record_ids: List[UUID] = []
            
            # Find primary key mapping
            pk_key, pk_model_field = self.find_primary_key_mapping(field_mappings)

            # Process entries in chunks for better memory management
            for i in range(0, len(entries), batch_size):
                chunk = entries[i:i + batch_size]
                for entry in chunk:
                    object_id, data = self.extract_data(entry, field_mappings)
                    
                    if object_id and data:
                        valid_records.append((object_id, data))
                        record_ids.append(object_id)
                    else:
                        result.failed += 1

            if not valid_records:
                return result.successful

            # Fetch existing records using the correct primary key field
            filter_kwargs = {f"{pk_model_field}__in": record_ids}
            existing_records = await sync_to_async(lambda: set(
                model.objects.filter(**filter_kwargs).values_list(pk_model_field, flat=True)
            ))()

            # Prepare records for database operations
            records_to_insert = []
            records_to_update = []

            for object_id, data in valid_records:
                data[pk_model_field] = object_id  # Use the correct primary key field
                if object_id in existing_records:
                    records_to_update.append(model(**data))
                else:
                    records_to_insert.append(model(**data))

            # Perform database operations
            await self.bulk_operations(model, records_to_insert, records_to_update, batch_size)
            result.successful = len(valid_records)

        except Exception as e:
            self.logger.error(f"Error processing entries: {str(e)}", exc_info=True)
            result.errors.append(str(e))
            raise

        return result.successful

    @sync_to_async
    def bulk_operations(self, model, records_to_insert, records_to_update, batch_size):
        """Perform bulk database operations with improved error handling."""
        with transaction.atomic():
            if records_to_insert:
                self.logger.info(f"Inserting {len(records_to_insert)} new records")
                model.objects.bulk_create(
                    records_to_insert,
                    batch_size=batch_size,
                    ignore_conflicts=True
                )

            if records_to_update:
                self.logger.info(f"Updating {len(records_to_update)} existing records")
                fields_to_update = list(self.get_model_fields(model))
                model.objects.bulk_update(
                    records_to_update,
                    fields=fields_to_update,
                    batch_size=batch_size
                )