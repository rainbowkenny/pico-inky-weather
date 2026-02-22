# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Webcam

- Device: `/dev/video0` (Logitech C920)
- For sharp photos: disable autofocus, set focus_absolute=50
  ```
  v4l2-ctl -d /dev/video0 --set-ctrl focus_automatic_continuous=0
  v4l2-ctl -d /dev/video0 --set-ctrl focus_absolute=50
  ffmpeg -f v4l2 -i /dev/video0 -vf "select=gte(n\,5)" -frames:v 1 -y /tmp/snap.jpg
  ```

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
