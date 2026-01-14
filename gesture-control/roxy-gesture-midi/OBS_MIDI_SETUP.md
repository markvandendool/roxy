# ROXY Hand Gesture -> OBS Setup Guide

## 1. Start the Gesture Controller
Open a terminal and run:
```bash
cd ~/.roxy/gesture-control/roxy-gesture-midi
source venv/bin/activate
./main.py
```
*Note: Make sure your webcam is connected.*

## 2. Configure OBS (obs-midi-mg)
1. Open OBS Studio.
2. Go to **Tools** -> **obs-midi-mg** (or finding the MIDI binding settings).
3. In the MIDI device list, locate **VirMIDI 3-0** (or similar "VirMIDI" device).
4. Click **Enable** for that device.

## 3. Map Gestures to Actions
Create the following bindings in the obs-midi-mg interface:

| Gesture | MIDI Message | OBS Action |
|---------|--------------|------------|
| **Point Up** ☝️ | CC 1 (Ch 0) | Switch to **Scene 1** |
| **Peace** ✌️ | CC 2 (Ch 0) | Switch to **Scene 2** |
| **3 Fingers** 🤟 | CC 3 (Ch 0) | Switch to **Scene 3** |
| **4 Fingers** 🖖 | CC 4 (Ch 0) | Switch to **Scene 4** |
| **Rock On** 🤘 | CC 5 (Ch 0) | Switch to **Scene 5** |
| **Thumbs Up** 👍 | CC 10 (Ch 0) | **Start Recording** |
| **Swipe Down** 👇 | CC 11 (Ch 0) | **Stop Recording** |
| **Pinch** 👌 | CC 20 (Ch 0) | Source Toggle: **Camera** |
| **Fist** ✊ | CC 23 (Ch 0) | Source Toggle: **Mute Mic** |

### How to Bind:
1. Click **Add Binding**.
2. Perform the captured MIDI message (or select **Control Change** manually).
   - Channel: 0 (or 1)
   - Control Number: (see table above)
3. Select the **Type** (e.g., "Main - Switch Scene").
4. Select the target (e.g., "Scene 1").

## 4. Testing
1. Ensure the Python script is running.
2. Hold your hand up to the camera.
3. Make a **Peace Sign**.
4. OBS should switch to Scene 2!
