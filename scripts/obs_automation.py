
#!/usr/bin/env python3
"""OBS Automation Helper"""
import obsws_python as obs
import os
from pathlib import Path

class OBSController:
    def __init__(self):
        self.password = os.getenv('OBS_WEBSOCKET_PASSWORD', '')
        self.port = int(os.getenv('OBS_WEBSOCKET_PORT', '4455'))
        self.client = None
        
    def connect(self):
        try:
            self.client = obs.ReqClient(host='localhost', port=self.port, password=self.password)
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def start_recording(self):
        if not self.client:
            if not self.connect():
                return False
        try:
            self.client.start_record()
            return True
        except Exception as e:
            print(f"Failed to start recording: {e}")
            return False
    
    def stop_recording(self):
        if not self.client:
            if not self.connect():
                return False
        try:
            self.client.stop_record()
            return True
        except Exception as e:
            print(f"Failed to stop recording: {e}")
            return False
    
    def get_recording_status(self):
        if not self.client:
            if not self.connect():
                return None
        try:
            status = self.client.get_record_status()
            return status
        except Exception as e:
            print(f"Failed to get status: {e}")
            return None

if __name__ == '__main__':
    import sys
    controller = OBSController()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'start':
            controller.start_recording()
        elif sys.argv[1] == 'stop':
            controller.stop_recording()
        elif sys.argv[1] == 'status':
            print(controller.get_recording_status())
    else:
        print('Usage: obs_automation.py [start|stop|status]')
