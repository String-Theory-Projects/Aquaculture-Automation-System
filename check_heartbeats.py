#!/usr/bin/env python3
"""
Quick script to check if heartbeats are being written to Redis.
Run this to diagnose heartbeat issues.

Usage:
    cd Future-Fish-Dashboard
    python check_heartbeats.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FutureFish.settings.dev')
django.setup()

import json
from datetime import datetime
from django.utils import timezone as django_timezone
from mqtt_client.bridge import get_redis_client

def check_heartbeats():
    """Check all heartbeat keys in Redis"""
    try:
        redis_client = get_redis_client()
        
        heartbeat_keys = [
            'health:mqtt_client',
            'health:mqtt_listener',
            'health:celery_worker',
            'health:celery_beat'
        ]
        
        print("=" * 60)
        print("Heartbeat Status Check")
        print("=" * 60)
        
        for key in heartbeat_keys:
            data = redis_client.get(key)
            ttl = redis_client.ttl(key)
            
            if data:
                try:
                    heartbeat = json.loads(data.decode('utf-8'))
                    timestamp_str = heartbeat.get('timestamp')
                    
                    if timestamp_str:
                        # Parse timestamp - fromisoformat handles timezone info automatically
                        heartbeat_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        # fromisoformat should return timezone-aware datetime, but ensure it is
                        if heartbeat_time.tzinfo is None:
                            heartbeat_time = django_timezone.make_aware(heartbeat_time)
                        heartbeat_age = (django_timezone.now() - heartbeat_time).total_seconds()
                        heartbeat_source = heartbeat.get('source', 'unknown')
                        
                        # Determine status based on age and source
                        if heartbeat_age < 60:
                            if heartbeat_source == 'health_server':
                                status = "✅ RECENT (from health server)"
                            elif heartbeat_source == 'scheduled_task':
                                status = "⚠️ RECENT (from scheduled task - service may not be running)"
                            else:
                                status = f"✅ RECENT (source: {heartbeat_source})"
                        else:
                            status = "⚠️ STALE"
                        
                        print(f"\n{key}:")
                        print(f"  Status: {status}")
                        print(f"  Age: {heartbeat_age:.1f} seconds")
                        print(f"  Source: {heartbeat_source}")
                        print(f"  TTL: {ttl} seconds")
                        print(f"  Data: {json.dumps(heartbeat, indent=2)}")
                    else:
                        print(f"\n{key}: ⚠️ Missing timestamp")
                        print(f"  Data: {json.dumps(heartbeat, indent=2)}")
                except Exception as e:
                    print(f"\n{key}: ❌ Error parsing: {e}")
                    print(f"  Raw data: {data}")
            else:
                print(f"\n{key}: ❌ NOT FOUND")
                print(f"  TTL: {ttl} (key doesn't exist)")
        
        print("\n" + "=" * 60)
        print("All heartbeat keys in Redis:")
        print("=" * 60)
        all_keys = list(redis_client.scan_iter(match="health:*"))
        if all_keys:
            for key in all_keys:
                print(f"  - {key.decode('utf-8')}")
        else:
            print("  (none found)")
        
    except Exception as e:
        print(f"❌ Error checking heartbeats: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_heartbeats()

