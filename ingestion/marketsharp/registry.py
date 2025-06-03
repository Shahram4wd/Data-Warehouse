from typing import Dict, Type
from django.db import models
import logging
import importlib
from pathlib import Path

class ProcessorRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.processors = {}
            cls._instance.endpoints = {}
            cls._instance.models = {}
            cls._instance.auto_discover()  # Auto-discover on instantiation
        return cls._instance
    
    def register(self, endpoint: str, api_url: str, model: Type[models.Model], processor_class: Type):
        """Register a new processor with its associated endpoint, URL, and model."""
        self.processors[endpoint] = processor_class
        self.endpoints[endpoint] = api_url
        self.models[endpoint] = model
    
    @classmethod
    def get_instance(cls):
        return cls()
    
    def auto_discover(self):
        """Automatically discover and register all processors in the data_import/processors directory."""
        current_dir = Path(__file__).parent
        processors_dir = current_dir / 'processors'
        
        if not processors_dir.exists():
            logging.warning(f"Processors directory not found at {processors_dir}")
            return
            
        for file in processors_dir.glob('*.py'):
            if file.name.startswith('_'):
                continue
            
            module_name = f"ingestion.marketsharp.processors.{file.stem}"  # Updated module path
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, 'register_processor'):
                    module.register_processor(self)
            except ImportError as e:
                logging.error(f"Failed to import processor module {module_name}: {e}")
                logging.error(f"Make sure all required dependencies are available")
