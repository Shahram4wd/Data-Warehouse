"""
Unit Tests for CRM Command Flag Validation

These tests verify that all CRM commands follow standardized flag patterns
without making any API calls or importing real data.

Test Type: UNIT (Safe, Fast, No External Dependencies)
Data Usage: MOCKED (No real API calls)
Duration: < 30 seconds
"""

import pytest
from django.core.management import get_commands
from django.core.management.base import BaseCommand
from django.core.management import load_command_class
import argparse

class TestFlagValidation:
    """Test that all CRM commands have standardized flags"""
    
    REQUIRED_FLAGS = [
        '--dry-run',      # Test mode without DB writes
        '--debug',        # Verbose logging
        '--batch-size',   # Records per batch
        '--full',         # Full sync (not --full-sync)
        '--quiet',        # Suppress non-error output
        '--force',        # Overwrite existing
    ]
    
    RECOMMENDED_FLAGS = [
        '--start-date',      # Start date for sync
        '--end-date',        # End date for sync
    ]
    
    def get_crm_commands(self):
        """Discover all CRM sync commands"""
        from django.core.management import get_commands
        all_commands = get_commands()
        
        # Filter for sync commands (excluding db_ commands which are database-only)
        crm_commands = [
            cmd for cmd in all_commands.keys() 
            if cmd.startswith('sync_') and not cmd.endswith('_test') and 'ingestion' in all_commands[cmd]
        ]
        return sorted(crm_commands)
    
    def test_all_crm_commands_discoverable(self):
        """Test that CRM commands can be discovered and imported"""
        crm_commands = self.get_crm_commands()
        
        # Should have commands from all 9 CRM systems
        assert len(crm_commands) >= 15, f"Expected 15+ CRM commands, found {len(crm_commands)}: {crm_commands}"
        
        # Check we have commands from each CRM system
        crm_systems = ['arrivy', 'callrail', 'five9', 'genius', 'gsheet', 
                      'hubspot', 'leadconduit', 'salespro', 'salesrabbit']
        
        for system in crm_systems:
            system_commands = [cmd for cmd in crm_commands if system in cmd]
            assert len(system_commands) > 0, f"No commands found for CRM system: {system}"
        
        print(f"✅ Discovered {len(crm_commands)} CRM commands across {len(crm_systems)} systems")
    
    def test_commands_can_be_imported(self):
        """Test that all CRM commands can be imported without errors"""
        crm_commands = self.get_crm_commands()
        failed_imports = []
        
        for command_name in crm_commands:
            try:
                command_class = load_command_class('ingestion', command_name)
                assert issubclass(command_class, BaseCommand)
            except Exception as e:
                failed_imports.append(f"{command_name}: {str(e)}")
        
        assert len(failed_imports) == 0, f"Failed to import commands: {failed_imports}"
        print(f"✅ Successfully imported {len(crm_commands)} CRM commands")
    
    def test_required_flags_present(self):
        """Test that all CRM commands have required standardized flags"""
        crm_commands = self.get_crm_commands()
        missing_flags = {}
        
        for command_name in crm_commands:
            try:
                command_class = load_command_class('ingestion', command_name)
                command_instance = command_class()
                
                # Get the argument parser
                parser = argparse.ArgumentParser()
                command_instance.add_arguments(parser)
                
                # Extract all argument names
                argument_names = []
                for action in parser._actions:
                    if hasattr(action, 'option_strings'):
                        argument_names.extend(action.option_strings)
                
                # Check for required flags
                command_missing = []
                for required_flag in self.REQUIRED_FLAGS:
                    if required_flag not in argument_names:
                        command_missing.append(required_flag)
                
                if command_missing:
                    missing_flags[command_name] = command_missing
                    
            except Exception as e:
                missing_flags[command_name] = f"Error loading command: {str(e)}"
        
        if missing_flags:
            error_msg = "Commands missing required flags:\n"
            for cmd, flags in missing_flags.items():
                error_msg += f"  {cmd}: {flags}\n"
            pytest.fail(error_msg)
        
        print(f"✅ All {len(crm_commands)} commands have required flags")
    
    def test_deprecated_flags_removed(self):
        """Test that deprecated flags have been removed"""
        crm_commands = self.get_crm_commands()
        deprecated_flags = ['--since', '--full-sync', '--force-overwrite']
        commands_with_deprecated = {}
        
        for command_name in crm_commands:
            try:
                command_class = load_command_class('ingestion', command_name)
                command_instance = command_class()
                
                parser = argparse.ArgumentParser()
                command_instance.add_arguments(parser)
                
                argument_names = []
                for action in parser._actions:
                    if hasattr(action, 'option_strings'):
                        argument_names.extend(action.option_strings)
                
                found_deprecated = [flag for flag in deprecated_flags if flag in argument_names]
                if found_deprecated:
                    commands_with_deprecated[command_name] = found_deprecated
                    
            except Exception as e:
                continue  # Skip commands that can't be loaded
        
        if commands_with_deprecated:
            error_msg = "Commands still using deprecated flags:\n"
            for cmd, flags in commands_with_deprecated.items():
                error_msg += f"  {cmd}: {flags}\n"
            pytest.fail(error_msg)
        
        print(f"✅ No deprecated flags found in {len(crm_commands)} commands")
    
    @pytest.mark.parametrize("command_name", [
        'sync_arrivy_entities', 'sync_arrivy_all',
        'sync_callrail_calls', 'sync_callrail_all',
        'sync_hubspot_contacts', 'sync_hubspot_all'
    ])
    def test_specific_command_flag_compliance(self, command_name):
        """Test specific high-priority commands for complete flag compliance"""
        try:
            command_class = load_command_class('ingestion', command_name)
            command_instance = command_class()
            
            parser = argparse.ArgumentParser()
            command_instance.add_arguments(parser)
            
            argument_names = []
            for action in parser._actions:
                if hasattr(action, 'option_strings'):
                    argument_names.extend(action.option_strings)
            
            # Check all required and recommended flags
            all_expected = self.REQUIRED_FLAGS + self.RECOMMENDED_FLAGS
            missing = [flag for flag in all_expected if flag not in argument_names]
            
            if missing:
                pytest.fail(f"Command {command_name} missing flags: {missing}")
            
            print(f"✅ {command_name} has all standardized flags")
            
        except ImportError:
            pytest.skip(f"Command {command_name} not available")
