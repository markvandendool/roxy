# Mac Pro Linux Hardware Notes

## Audio Configuration

### Stereo Split Setup (2026-01-09)

**Configuration:** Split stereo audio across two monitors for proper L/R separation.

| Channel | Monitor | GPU Output | PipeWire Node |
|---------|---------|------------|---------------|
| Left (FL) | TCL 43S425CA | pro-output-11 | alsa_output.pci-0000_09_00.1.pro-output-11 |
| Right (FR) | RCA | pro-output-9 | alsa_output.pci-0000_09_00.1.pro-output-9 |

**Note:** Both monitors connect to the 6800XT (Navi 21) for video, but audio routes through the 5700X (Navi 10) GPU. This is Mac Pro Thunderbolt passthrough behavior.

**Files:**
- PipeWire config: `~/.config/pipewire/pipewire.conf.d/99-stereo-split-tcl-rca.conf`
- Systemd service: `~/.config/systemd/user/stereo-split-links.service`

**To switch back to single monitor audio:**
```bash
pactl set-default-sink alsa_output.pci-0000_09_00.1.pro-output-9  # RCA only
# or
pactl set-default-sink alsa_output.pci-0000_09_00.1.pro-output-11  # TCL only
```

**To use both monitors (same audio on both):**
```bash
pactl load-module module-combine-sink sink_name=dual-monitor slaves=alsa_output.pci-0000_09_00.1.pro-output-9,alsa_output.pci-0000_09_00.1.pro-output-11
pactl set-default-sink dual-monitor
```

---

## Display Configuration

| Monitor | Connection | GPU | DRM Output |
|---------|------------|-----|------------|
| TCL 43S425CA | HDMI-to-USB-C | 6800XT (card0) | DP-3 |
| Samsung U32R59x | DisplayPort | 6800XT (card0) | DP-5 |
| RCA | HDMI | 6800XT (card0) | DP-6 |

---

## GPU Information

| Card | Model | PCI | Use |
|------|-------|-----|-----|
| card0 (DRM) / card1 (ALSA) | Navi 21 (6800XT) | 14:00.0 | Video output |
| card1 (DRM) / card0 (ALSA) | Navi 10 (W5700X) | 09:00.0 | Audio passthrough |

**Note:** DRM and ALSA card numbering is swapped!
