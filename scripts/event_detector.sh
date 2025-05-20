#!/bin/bash

# Define the directory to monitor
TARGET_DIR="/home/zhijie/Desktop/github/uam/cloud_video_editor/fabric-video-editor-master"

# Verify that inotifywait is installed
if ! command -v inotifywait &> /dev/null; then
    echo "inotify-tools is not installed. Please install it first:"
    echo "sudo apt-get install inotify-tools"
    exit 1
fi

# Verify the target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Target directory does not exist: $TARGET_DIR"
    exit 1
fi

echo "Monitoring directory: $TARGET_DIR"
echo "Press Ctrl+C to stop monitoring"
echo "--------------------------------"

# Monitor for create, modify, delete, move, and attribute changes
inotifywait -m -r --format "%T %e %w%f" --timefmt "%F %T" \
    -e create -e modify -e delete -e moved_to -e moved_from -e attrib \
    "$TARGET_DIR" | while read -r line
do
    # Extract the timestamp and event info
    timestamp=$(echo "$line" | awk '{print $1 " " $2}')
    event=$(echo "$line" | awk '{print $3}')
    file=$(echo "$line" | awk '{$1=$2=$3=""; print $0}' | sed 's/^ *//')
    
    # Color coding for different event types
    case "$event" in
        *CREATE*|*MOVED_TO*)
            # Green for creation events
            echo -e "\e[32m[$timestamp] $event $file\e[0m"
            ;;
        *MODIFY*|*ATTRIB*)
            # Yellow for modification events
            echo -e "\e[33m[$timestamp] $event $file\e[0m"
            ;;
        *DELETE*|*MOVED_FROM*)
            # Red for deletion events
            echo -e "\e[31m[$timestamp] $event $file\e[0m"
            ;;
        *)
            # Default color for other events
            echo "[$timestamp] $event $file"
            ;;
    esac
done