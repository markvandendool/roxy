# Fix Taskbar Stats Overlapping Date

## Quick Fix:

1. **Open Extension Manager:**
   ```bash
   gnome-extensions-app
   ```

2. **Find "Vitals" extension**

3. **Click the gear icon ⚙️**

4. **In Settings, adjust:**
   - **Font Size**: Set to 9 or 10 (default is usually 12)
   - **Compact Mode**: Enable this
   - **Show Icons**: Can disable to save space
   - **Update Interval**: Keep at 2 seconds (faster = more CPU)

5. **Or disable some metrics** to reduce width:
   - Uncheck metrics you don't need
   - Keep: CPU, GPU1, GPU2, RAM
   - Optional: Disk, Network, Temp

6. **Restart GNOME Shell:**
   - Press `Alt+F2`
   - Type `r`
   - Press `Enter`

## Alternative: Move Date/Time

If stats still overlap, you can move the clock:
```bash
# Install Clock Override extension
# Or adjust panel spacing
```

## Manual Config (if extension manager doesn't work):

The Vitals config is in:
`~/.local/share/gnome-shell/extensions/vitals@CoreCoding.com/schemas/`

Edit with:
```bash
dconf-editor
Navigate to: /org/gnome/shell/extensions/vitals/
Set font-size to 9
Set compact-mode to true
```
