"""
Data Access Service

Provides paginated access to CRM model data with search capabilities,
field introspection, and metadata extraction for the dashboard tables.
"""
import importlib
import inspect
from typing import Dict, List, Optional, Any, Type
from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


class DataAccessService:
    """Service for accessing and paginating CRM model data"""
    
    def __init__(self):
        self.field_type_mapping = {
            'CharField': 'text',
            'TextField': 'text',
            'IntegerField': 'number',
            'BigIntegerField': 'number',
            'DecimalField': 'number',
            'FloatField': 'number',
            'BooleanField': 'boolean',
            'DateField': 'date',
            'DateTimeField': 'datetime',
            'TimeField': 'time',
            'EmailField': 'email',
            'URLField': 'url',
            'ForeignKey': 'foreign_key',
            'OneToOneField': 'foreign_key',
            'ManyToManyField': 'many_to_many',
            'JSONField': 'json'
        }
    
    def get_model_class(self, crm_source: str, model_name: str) -> Optional[Type[models.Model]]:
        """Get Django model class by CRM source and model name"""
        try:
            # Import the CRM module
            module_path = f'ingestion.models.{crm_source}'
            module = importlib.import_module(module_path)
            
            # Find the model class
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, models.Model) and 
                    obj != models.Model and
                    name.lower() == model_name.lower()):
                    return obj
            
            logger.warning(f"Model {model_name} not found in {module_path}")
            return None
            
        except ImportError as e:
            logger.error(f"Could not import CRM module {crm_source}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting model class {crm_source}.{model_name}: {e}")
            return None
    
    def get_model_metadata(self, model_class: Type[models.Model]) -> Dict[str, Any]:
        """Get comprehensive metadata for a Django model"""
        try:
            fields_info = []
            
            # Get all model fields
            for field in model_class._meta.fields:
                field_info = self._get_field_metadata(field)
                fields_info.append(field_info)
            
            # Get many-to-many fields
            for field in model_class._meta.many_to_many:
                field_info = self._get_field_metadata(field)
                fields_info.append(field_info)
            
            metadata = {
                'model_name': model_class.__name__,
                'table_name': model_class._meta.db_table,
                'verbose_name': str(model_class._meta.verbose_name),
                'verbose_name_plural': str(model_class._meta.verbose_name_plural),
                'fields': fields_info,
                'total_fields': len(fields_info),
                'primary_key_field': model_class._meta.pk.name,
                'ordering': list(model_class._meta.ordering) if model_class._meta.ordering else [],
                'searchable_fields': self._get_searchable_fields(fields_info),
                'display_fields': self._get_display_fields(fields_info)
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting model metadata: {e}")
            return {}
    
    def _get_field_metadata(self, field) -> Dict[str, Any]:
        """Get metadata for a single model field"""
        field_class_name = field.__class__.__name__
        field_type = self.field_type_mapping.get(field_class_name, 'unknown')
        
        field_info = {
            'name': field.name,
            'verbose_name': str(field.verbose_name),
            'type': field_type,
            'field_class': field_class_name,
            'null': field.null,
            'blank': field.blank,
            'primary_key': getattr(field, 'primary_key', False),
            'unique': getattr(field, 'unique', False),
            'db_index': getattr(field, 'db_index', False),
            'editable': field.editable,
            'searchable': self._is_field_searchable(field),
            'sortable': self._is_field_sortable(field),
            'display_priority': self._get_field_display_priority(field)
        }
        
        # Add field-specific attributes
        if hasattr(field, 'max_length') and field.max_length:
            field_info['max_length'] = field.max_length
        
        if hasattr(field, 'choices') and field.choices:
            field_info['choices'] = list(field.choices)
            field_info['has_choices'] = True
        else:
            field_info['has_choices'] = False
        
        if field_type == 'foreign_key':
            field_info['related_model'] = field.related_model.__name__
            field_info['related_field'] = field.target_field.name
        
        if hasattr(field, 'default') and field.default is not models.NOT_PROVIDED:
            field_info['has_default'] = True
            field_info['default'] = str(field.default) if callable(field.default) else field.default
        else:
            field_info['has_default'] = False
        
        return field_info
    
    def _is_field_searchable(self, field) -> bool:
        """Determine if a field should be searchable"""
        searchable_types = ['CharField', 'TextField', 'EmailField', 'URLField']
        return field.__class__.__name__ in searchable_types
    
    def _is_field_sortable(self, field) -> bool:
        """Determine if a field should be sortable"""
        non_sortable_types = ['TextField', 'JSONField', 'ManyToManyField']
        return field.__class__.__name__ not in non_sortable_types
    
    def _get_field_display_priority(self, field) -> int:
        """Get display priority for field (lower = higher priority)"""
        if field.primary_key:
            return 1
        elif field.name in ['name', 'title', 'email', 'phone']:
            return 2
        elif field.name in ['created_at', 'updated_at', 'status']:
            return 3
        elif field.__class__.__name__ in ['CharField', 'EmailField']:
            return 4
        elif field.__class__.__name__ in ['DateTimeField', 'DateField']:
            return 5
        else:
            return 6
    
    def _get_searchable_fields(self, fields_info: List[Dict]) -> List[str]:
        """Get list of fields that can be searched"""
        return [field['name'] for field in fields_info if field['searchable']]
    
    def _get_display_fields(self, fields_info: List[Dict]) -> List[str]:
        """Get fields to display by default (top priority fields)"""
        sorted_fields = sorted(fields_info, key=lambda x: x['display_priority'])
        return [field['name'] for field in sorted_fields[:6]]  # Top 6 fields
    
    def get_model_data(self, 
                      model_class: Type[models.Model], 
                      page: int = 1, 
                      per_page: int = 25, 
                      search: str = None,
                      order_by: str = None,
                      filters: Dict = None) -> Dict[str, Any]:
        """Get paginated model data with search and filtering"""
        try:
            # Start with all objects
            queryset = model_class.objects.all()
            
            # Apply search if provided
            if search:
                queryset = self._apply_search_filter(queryset, model_class, search)
            
            # Apply additional filters
            if filters:
                queryset = self._apply_filters(queryset, filters)
            
            # Apply ordering
            if order_by:
                # Handle descending order (prefix with -)
                if order_by.startswith('-'):
                    field_name = order_by[1:]
                    if self._is_valid_field(model_class, field_name):
                        queryset = queryset.order_by(order_by)
                else:
                    if self._is_valid_field(model_class, order_by):
                        queryset = queryset.order_by(order_by)
            else:
                # Default ordering - try primary key or created_at
                if hasattr(model_class, 'created_at'):
                    queryset = queryset.order_by('-created_at')
                else:
                    queryset = queryset.order_by('-pk')
            
            # Get total count before pagination
            total_count = queryset.count()
            
            # Apply pagination
            paginator = Paginator(queryset, per_page)
            
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
            
            # Convert model instances to dictionaries
            data = []
            for instance in page_obj.object_list:
                instance_data = self._model_instance_to_dict(instance)
                data.append(instance_data)
            
            pagination_info = {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': total_count,
                'items_per_page': per_page,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                'start_index': page_obj.start_index(),
                'end_index': page_obj.end_index()
            }
            
            return {
                'data': data,
                'pagination': pagination_info,
                'search_query': search,
                'order_by': order_by,
                'filters_applied': filters or {},
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error getting model data: {e}")
            return {
                'data': [],
                'pagination': {
                    'current_page': 1,
                    'total_pages': 0,
                    'total_items': 0,
                    'items_per_page': per_page,
                    'has_previous': False,
                    'has_next': False
                },
                'error': str(e),
                'success': False
            }
    
    def _apply_search_filter(self, queryset, model_class: Type[models.Model], search: str):
        """Apply search filter across searchable fields"""
        if not search.strip():
            return queryset
        
        # Get searchable fields
        metadata = self.get_model_metadata(model_class)
        searchable_fields = metadata.get('searchable_fields', [])
        
        if not searchable_fields:
            return queryset
        
        # Build Q objects for OR search across fields
        search_q = Q()
        search_terms = search.strip().split()
        
        for term in search_terms:
            term_q = Q()
            for field in searchable_fields:
                # Use icontains for case-insensitive partial matching
                term_q |= Q(**{f'{field}__icontains': term})
            search_q &= term_q
        
        return queryset.filter(search_q)
    
    def _apply_filters(self, queryset, filters: Dict):
        """Apply additional filters to queryset"""
        for field, value in filters.items():
            if value is not None and value != '':
                try:
                    # Handle different filter types
                    if isinstance(value, dict):
                        # Range filters: {'field': {'gte': value1, 'lte': value2}}
                        for lookup, lookup_value in value.items():
                            queryset = queryset.filter(**{f'{field}__{lookup}': lookup_value})
                    else:
                        # Exact match filter
                        queryset = queryset.filter(**{field: value})
                except Exception as e:
                    logger.warning(f"Error applying filter {field}={value}: {e}")
        
        return queryset
    
    def _is_valid_field(self, model_class: Type[models.Model], field_name: str) -> bool:
        """Check if field name is valid for the model"""
        try:
            model_class._meta.get_field(field_name)
            return True
        except:
            return False
    
    def _model_instance_to_dict(self, instance) -> Dict[str, Any]:
        """Convert model instance to dictionary with proper value formatting"""
        data = {}
        
        for field in instance._meta.fields:
            field_name = field.name
            value = getattr(instance, field_name)
            
            # Format value based on field type
            if value is None:
                data[field_name] = None
            elif field.__class__.__name__ == 'DateTimeField':
                data[field_name] = value.isoformat() if value else None
            elif field.__class__.__name__ == 'DateField':
                data[field_name] = value.isoformat() if value else None
            elif field.__class__.__name__ == 'TimeField':
                data[field_name] = value.strftime('%H:%M:%S') if value else None
            elif field.__class__.__name__ == 'DecimalField':
                data[field_name] = float(value) if value is not None else None
            elif field.__class__.__name__ in ['ForeignKey', 'OneToOneField']:
                # For foreign keys, include both ID and string representation
                if value:
                    data[field_name] = {
                        'id': value.pk,
                        'display': str(value)
                    }
                else:
                    data[field_name] = None
            elif field.__class__.__name__ == 'JSONField':
                data[field_name] = value  # JSONField already handles serialization
            else:
                data[field_name] = value
        
        # Add many-to-many relationships (limited to avoid huge payloads)
        for field in instance._meta.many_to_many:
            field_name = field.name
            related_objects = getattr(instance, field_name).all()[:5]  # Limit to 5
            data[field_name] = [
                {'id': obj.pk, 'display': str(obj)} 
                for obj in related_objects
            ]
            if getattr(instance, field_name).count() > 5:
                data[f'{field_name}_count'] = getattr(instance, field_name).count()
        
        # Add primary key if not already included
        if 'id' not in data:
            data['id'] = instance.pk
        
        return data
    
    def get_record_detail(self, model_class: Type[models.Model], record_id: Any) -> Dict[str, Any]:
        """Get detailed information for a specific record"""
        try:
            instance = model_class.objects.get(pk=record_id)
            
            # Get full record data including all relationships
            data = self._model_instance_to_dict(instance)
            
            # Add additional metadata
            metadata = {
                'model_name': model_class.__name__,
                'record_id': record_id,
                'string_representation': str(instance),
                'last_modified': getattr(instance, 'updated_at', None) or getattr(instance, 'modified_at', None),
                'created': getattr(instance, 'created_at', None)
            }
            
            return {
                'success': True,
                'data': data,
                'metadata': metadata
            }
            
        except model_class.DoesNotExist:
            return {
                'success': False,
                'error': f'Record with ID {record_id} not found'
            }
        except Exception as e:
            logger.error(f"Error getting record detail: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_model_statistics(self, model_class: Type[models.Model]) -> Dict[str, Any]:
        """Get statistical information about a model"""
        try:
            stats = {
                'total_records': model_class.objects.count(),
                'model_name': model_class.__name__,
                'table_name': model_class._meta.db_table
            }
            
            # Add date-based statistics if date fields exist
            if hasattr(model_class, 'created_at'):
                from django.db.models import Count
                from django.utils import timezone
                from datetime import timedelta
                
                now = timezone.now()
                last_24h = now - timedelta(days=1)
                last_week = now - timedelta(days=7)
                last_month = now - timedelta(days=30)
                
                stats.update({
                    'created_last_24h': model_class.objects.filter(created_at__gte=last_24h).count(),
                    'created_last_week': model_class.objects.filter(created_at__gte=last_week).count(),
                    'created_last_month': model_class.objects.filter(created_at__gte=last_month).count()
                })
            
            # Add status-based statistics if status field exists
            if hasattr(model_class, 'status'):
                from django.db.models import Count
                status_distribution = model_class.objects.values('status').annotate(
                    count=Count('status')
                ).order_by('-count')
                stats['status_distribution'] = list(status_distribution)
            
            return {
                'success': True,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting model statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
