#!/usr/bin/env python3
"""
ROXY OBS Control Script
Controls OBS via WebSocket API (port 4455)

Usage:
  ./obs-control.py status          # Show current status
  ./obs-control.py scenes          # List all scenes
  ./obs-control.py switch <name>   # Switch to scene
  ./obs-control.py record start    # Start recording
  ./obs-control.py record stop     # Stop recording
  ./obs-control.py record toggle   # Toggle recording
  ./obs-control.py stream start    # Start streaming
  ./obs-control.py stream stop     # Stop streaming
  ./obs-control.py replay save     # Save replay buffer
  ./obs-control.py screenshot      # Take screenshot
"""
import sys
import obsws_python as obs

HOST = 'localhost'
PORT = 4455
PASSWORD = 'nikkisixx'

def get_client():
    return obs.ReqClient(host=HOST, port=PORT, password=PASSWORD, timeout=10)

def cmd_status():
    cl = get_client()

    # Scene
    scene = cl.get_current_program_scene()
    print(f"Scene: {scene.scene_name}")

    # Video
    video = cl.get_video_settings()
    print(f"Video: {video.base_width}x{video.base_height} @ {video.fps_numerator}fps")

    # Recording
    rec = cl.get_record_status()
    if rec.output_active:
        print(f"Recording: ACTIVE ({rec.output_timecode})")
    else:
        print("Recording: stopped")

    # Streaming
    stream = cl.get_stream_status()
    if stream.output_active:
        print(f"Streaming: LIVE ({stream.output_timecode})")
    else:
        print("Streaming: offline")

    # Stats
    stats = cl.get_stats()
    print(f"CPU: {stats.cpu_usage:.1f}%, Mem: {stats.memory_usage:.0f}MB, Render: {stats.average_frame_render_time:.1f}ms")

    cl.disconnect()

def cmd_scenes():
    cl = get_client()
    scenes = cl.get_scene_list()
    current = cl.get_current_program_scene()

    print("Scenes:")
    for s in scenes.scenes:
        marker = "→ " if s['sceneName'] == current.scene_name else "  "
        items = cl.get_scene_item_list(name=s['sceneName'])
        sources = [i['sourceName'] for i in items.scene_items]
        print(f"{marker}{s['sceneName']}: {sources if sources else '(empty)'}")

    cl.disconnect()

def cmd_switch(scene_name):
    cl = get_client()
    cl.set_current_program_scene(name=scene_name)
    print(f"Switched to: {scene_name}")
    cl.disconnect()

def cmd_record(action):
    cl = get_client()
    if action == 'start':
        cl.start_record()
        print("Recording started")
    elif action == 'stop':
        result = cl.stop_record()
        print(f"Recording stopped: {result.output_path}")
    elif action == 'toggle':
        cl.toggle_record()
        rec = cl.get_record_status()
        print(f"Recording: {'ACTIVE' if rec.output_active else 'stopped'}")
    else:
        print(f"Unknown action: {action}")
    cl.disconnect()

def cmd_stream(action):
    cl = get_client()
    if action == 'start':
        cl.start_stream()
        print("Streaming started")
    elif action == 'stop':
        cl.stop_stream()
        print("Streaming stopped")
    elif action == 'toggle':
        cl.toggle_stream()
        stream = cl.get_stream_status()
        print(f"Streaming: {'LIVE' if stream.output_active else 'offline'}")
    else:
        print(f"Unknown action: {action}")
    cl.disconnect()

def cmd_replay(action):
    cl = get_client()
    if action == 'save':
        cl.save_replay_buffer()
        print("Replay saved")
    elif action == 'start':
        cl.start_replay_buffer()
        print("Replay buffer started")
    elif action == 'stop':
        cl.stop_replay_buffer()
        print("Replay buffer stopped")
    else:
        print(f"Unknown action: {action}")
    cl.disconnect()

def cmd_screenshot():
    cl = get_client()
    import datetime
    filename = f"/home/mark/Videos/screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    scene = cl.get_current_program_scene()
    cl.save_source_screenshot(
        source_name=scene.scene_name,
        image_format="png",
        image_file_path=filename,
        image_width=1920,
        image_height=1080
    )
    print(f"Screenshot saved: {filename}")
    cl.disconnect()

def cmd_help():
    print(__doc__)

def main():
    if len(sys.argv) < 2:
        cmd_help()
        return

    cmd = sys.argv[1].lower()

    try:
        if cmd == 'status':
            cmd_status()
        elif cmd == 'scenes':
            cmd_scenes()
        elif cmd == 'switch' and len(sys.argv) > 2:
            cmd_switch(sys.argv[2])
        elif cmd == 'record' and len(sys.argv) > 2:
            cmd_record(sys.argv[2])
        elif cmd == 'stream' and len(sys.argv) > 2:
            cmd_stream(sys.argv[2])
        elif cmd == 'replay' and len(sys.argv) > 2:
            cmd_replay(sys.argv[2])
        elif cmd == 'screenshot':
            cmd_screenshot()
        elif cmd in ['help', '-h', '--help']:
            cmd_help()
        else:
            print(f"Unknown command: {cmd}")
            cmd_help()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
