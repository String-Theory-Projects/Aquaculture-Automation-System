#!/usr/bin/env python3
"""
Django management command to fix stuck commands and automation executions.

This command identifies and fixes commands that are stuck in intermediate states
and automation executions that never completed.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from automation.models import DeviceCommand, AutomationExecution

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix stuck commands and automation executions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--timeout-hours',
            type=int,
            default=1,
            help='Consider commands stuck after this many hours (default: 1)',
        )
        parser.add_argument(
            '--fix-all',
            action='store_true',
            help='Fix all stuck items, not just the most critical ones',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        timeout_hours = options['timeout_hours']
        fix_all = options['fix_all']

        self.stdout.write(
            self.style.SUCCESS(f'🔧 Fixing stuck commands and automations (timeout: {timeout_hours}h)')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('📋 DRY RUN MODE - No changes will be made'))

        # Calculate cutoff time
        cutoff_time = timezone.now() - timedelta(hours=timeout_hours)
        self.stdout.write(f'⏰ Cutoff time: {cutoff_time}')

        # Fix stuck commands
        stuck_commands = self._fix_stuck_commands(cutoff_time, dry_run, fix_all)

        # Fix stuck automation executions
        stuck_automations = self._fix_stuck_automations(cutoff_time, dry_run, fix_all)

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
        self.stdout.write(f'   Stuck commands fixed: {len(stuck_commands)}')
        self.stdout.write(f'   Stuck automations fixed: {len(stuck_automations)}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('💡 Run without --dry-run to apply fixes'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ All fixes applied successfully'))

    def _fix_stuck_commands(self, cutoff_time, dry_run, fix_all):
        """Fix stuck device commands"""
        self.stdout.write('\n🔧 Fixing stuck device commands...')

        # Find commands that are stuck in SENT status for too long
        stuck_commands = DeviceCommand.objects.filter(
            status='SENT',
            sent_at__lt=cutoff_time
        ).order_by('sent_at')

        if not stuck_commands.exists():
            self.stdout.write('   ✅ No stuck commands found')
            return []

        self.stdout.write(f'   📋 Found {stuck_commands.count()} stuck commands')

        fixed_commands = []
        for command in stuck_commands:
            self.stdout.write(f'   🔍 Command {command.command_id}: {command.command_type} - sent at {command.sent_at}')

            if not dry_run:
                try:
                    with transaction.atomic():
                        # Mark as timed out
                        command.timeout_command()
                        
                        # Update linked automation if exists
                        if command.automation_execution:
                            automation = command.automation_execution
                            # Calculate hours since sent for the message
                            hours_since_sent = (timezone.now() - command.sent_at).total_seconds() / 3600
                            automation.complete_execution(
                                False, 
                                f"Command timed out after {hours_since_sent:.1f}h (auto-fixed)"
                            )
                            self.stdout.write(f'      ✅ Updated automation {automation.id}')
                        
                        fixed_commands.append(command.command_id)
                        self.stdout.write(f'      ✅ Fixed command {command.command_id}')
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'      ❌ Error fixing command {command.command_id}: {e}')
                    )
            else:
                fixed_commands.append(command.command_id)
                self.stdout.write(f'      📝 Would fix command {command.command_id}')

        return fixed_commands

    def _fix_stuck_automations(self, cutoff_time, dry_run, fix_all):
        """Fix stuck automation executions"""
        self.stdout.write('\n🔧 Fixing stuck automation executions...')

        # Find automations that are stuck in EXECUTING status for too long
        stuck_automations = AutomationExecution.objects.filter(
            status='EXECUTING',
            started_at__lt=cutoff_time
        ).order_by('started_at')

        if not stuck_automations.exists():
            self.stdout.write('   ✅ No stuck automations found')
            return []

        self.stdout.write(f'   📋 Found {stuck_automations.count()} stuck automations')

        fixed_automations = []
        for automation in stuck_automations:
            self.stdout.write(f'   🔍 Automation {automation.id}: {automation.action} - started at {automation.started_at}')

            # Check if linked commands are completed
            linked_commands = automation.device_commands.all()
            if linked_commands.exists():
                command_statuses = [cmd.status for cmd in linked_commands]
                self.stdout.write(f'      📋 Linked commands: {command_statuses}')
                
                # If any command is completed/failed, sync the automation
                if any(status in ['COMPLETED', 'FAILED', 'TIMEOUT'] for status in command_statuses):
                    if not dry_run:
                        try:
                            with transaction.atomic():
                                # Find the most recent command status
                                latest_command = linked_commands.order_by('-updated_at').first()
                                
                                if latest_command.status == 'COMPLETED':
                                    automation.complete_execution(True, "Auto-synced from completed command")
                                    self.stdout.write(f'      ✅ Synced automation {automation.id} to COMPLETED')
                                elif latest_command.status in ['FAILED', 'TIMEOUT']:
                                    automation.complete_execution(False, f"Auto-synced from {latest_command.status.lower()} command")
                                    self.stdout.write(f'      ✅ Synced automation {automation.id} to FAILED')
                                
                                fixed_automations.append(automation.id)
                                
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'      ❌ Error syncing automation {automation.id}: {e}')
                            )
                    else:
                        fixed_automations.append(automation.id)
                        self.stdout.write(f'      📝 Would sync automation {automation.id}')
                else:
                    # All commands are still pending/sent - mark as failed due to timeout
                    if not dry_run:
                        try:
                            with transaction.atomic():
                                automation.complete_execution(
                                    False, 
                                    f"Automation timed out after {timeout_hours}h (auto-fixed)"
                                )
                                self.stdout.write(f'      ✅ Marked automation {automation.id} as failed (timeout)')
                                fixed_automations.append(automation.id)
                                
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'      ❌ Error fixing automation {automation.id}: {e}')
                            )
                    else:
                        fixed_automations.append(automation.id)
                        self.stdout.write(f'      📝 Would mark automation {automation.id} as failed (timeout)')
            else:
                # No linked commands - mark as failed
                if not dry_run:
                    try:
                        with transaction.atomic():
                            automation.complete_execution(
                                False, 
                                f"No linked commands found - marked as failed (auto-fixed)"
                            )
                            self.stdout.write(f'      ✅ Marked automation {automation.id} as failed (no commands)')
                            fixed_automations.append(automation.id)
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'      ❌ Error fixing automation {automation.id}: {e}')
                        )
                else:
                    fixed_automations.append(automation.id)
                    self.stdout.write(f'      📝 Would mark automation {automation.id} as failed (no commands)')

        return fixed_automations
