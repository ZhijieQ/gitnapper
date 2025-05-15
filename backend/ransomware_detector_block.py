#!/usr/bin/env python3
import subprocess
import re
import time
from collections import deque
import threading
import sys
import os

# Configuration
TARGET_DIR = "/home/zhijie/Desktop/github/uam/cloud_video_editor"
EVENT_THRESHOLD = 20  # Number of events to consider suspicious
TIME_WINDOW = 1       # Seconds to monitor for threshold
COOLDOWN_PERIOD = 1  # Seconds before sending another alert

class RansomwareDetector:
    def __init__(self):
        self.event_queue = deque(maxlen=EVENT_THRESHOLD * 2)
        self.last_alert_time = 0
        self.running = True
        self.lock = threading.Lock()
        self.protected = False  # Track if we've already protected the directory

    def verify_environment(self):
        """Verify all requirements are met"""
        # Check inotifywait exists
        if not os.path.exists('/usr/bin/inotifywait'):
            print("Error: inotifywait not found at /usr/bin/inotifywait")
            return False
        
        # Check target directory exists
        if not os.path.isdir(TARGET_DIR):
            print(f"Error: Target directory does not exist: {TARGET_DIR}")
            return False
            
        return True

    def parse_inotify_line(self, line):
        """Parse inotifywait output line into timestamp, event, and path"""
        try:
            match = re.match(r'\[([^\]]+)\] (\S+) (.*)', line.strip())
            if match:
                timestamp_str, event, path = match.groups()
                timestamp = time.mktime(time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S"))
                return timestamp, event, path
        except Exception as e:
            print(f"Error parsing line: {e}")
        return None, None, None

    def protect_directory(self):
        """Change directory permissions to make it inaccessible"""
        try:
            # Remove all permissions from the directory
            os.chmod(TARGET_DIR, 0o000)
            print(f"\n\033[1;31m[PROTECTED] Directory {TARGET_DIR} permissions changed to 000 (no access)\033[0m")
            self.protected = True
            return True
        except Exception as e:
            print(f"\n\033[1;31m[ERROR] Failed to protect directory: {e}\033[0m")
            return False

    def restore_directory(self):
        """Restore normal directory permissions"""
        try:
            # Set permissions back to normal (read/write/execute for owner)
            os.chmod(TARGET_DIR, 0o700)
            print(f"\n\033[1;32m[RESTORED] Directory {TARGET_DIR} permissions restored to 700\033[0m")
            self.protected = False
            return True
        except Exception as e:
            print(f"\n\033[1;31m[ERROR] Failed to restore directory: {e}\033[0m")
            return False

    def analyze_events(self):
        """Check if recent events exceed threshold"""
        with self.lock:
            now = time.time()
            while self.event_queue and (now - self.event_queue[0][0]) > TIME_WINDOW:
                self.event_queue.popleft()
            
            if len(self.event_queue) >= EVENT_THRESHOLD:
                if (now - self.last_alert_time) > COOLDOWN_PERIOD:
                    self.last_alert_time = now
                    return True
        return False

    def event_handler(self, line):
        """Process each inotify event"""
        timestamp, event, path = self.parse_inotify_line(line)
        if timestamp and event and path:
            with self.lock:
                self.event_queue.append((timestamp, event, path))
            
            if self.analyze_events() and not self.protected:
                print(f"\n\033[1;31m[WARNING] RANSOMWARE SUSPICION: {len(self.event_queue)} "
                      f"file changes detected in last {TIME_WINDOW} seconds!\033[0m")
                print("Recent changes:")
                for ts, ev, p in list(self.event_queue)[-10:]:
                    print(f"  {time.strftime('%H:%M:%S', time.localtime(ts))} {ev} {p}")
                print()
                
                # Protect the directory when suspicious activity is detected
                self.protect_directory()

    def start_monitoring(self):
        """Start the inotifywait subprocess and monitor its output"""
        cmd = [
            '/usr/bin/inotifywait', '-m', '-r',
            '--format', '[%T] %e %w%f',
            '--timefmt', '%F %T',
            '-e', 'create',
            '-e', 'delete',
            '-e', 'moved_to',
            '-e', 'moved_from',
            '-e', 'attrib',
            TARGET_DIR
        ]

        try:
            print(f"Starting monitoring on {TARGET_DIR}...")
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1) as proc:
                print(f"Monitoring active (PID: {proc.pid})")
                print(f"Alert threshold: {EVENT_THRESHOLD} events in {TIME_WINDOW} seconds")
                print("Press Ctrl+C to stop monitoring and restore permissions")
                
                while self.running:
                    line = proc.stdout.readline()
                    if not line:
                        if proc.poll() is not None:
                            break
                        continue
                    self.event_handler(line.strip())
                    
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            self.running = False
            if self.protected:
                self.restore_directory()

if __name__ == "__main__":
    detector = RansomwareDetector()
    
    if not detector.verify_environment():
        sys.exit(1)
    
    try:
        detector.start_monitoring()
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)