# Claude Notifications - Simple Setup

A minimal file-based notification system that alerts you when Claude needs your attention.

## How it Works

1. Claude writes a notification to a shared file
2. Host script watches the file and shows desktop notification
3. That's it!

## Setup

### On Your Host (Ubuntu)

1. **Copy this folder to your home directory:**
```bash
cp -r host-scripts ~/claude-notify
cd ~/claude-notify
```

2. **Run the watcher:**
```bash
./notify-watch.sh
```

Or run it in background:
```bash
nohup ./notify-watch.sh > /dev/null 2>&1 &
```

### In Container

Already configured! The volume mount in docker-compose.yaml connects:
- Container: `/workspace/.notifications`
- Host: `~/.claude-notifications`

## That's All!

Claude will notify you when:
- ❓ Clarification is needed
- 🚫 Claude is blocked  
- ✅ Task is completed
- ❌ Error occurs

## Test It

From inside container:
```bash
bash ~/.claude/hooks/notify.sh test "Test notification"
```

## Stop Notifications

Just kill the watcher:
```bash
pkill -f notify-watch.sh
```