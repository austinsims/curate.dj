#!/bin/bash

# Monitor the currently playing song in Icecast and send a redis
# notification to the 'now_playing' channel when it changes.

# Usage: monitor.sh /path/to/playlist.log

if [ "$#" -ne "1" ]
then
    echo "Usage: monitor.sh /path/to/playlist.log"
    exit 1
fi

LOGFILE=$1

PREV_SONG=""
while true
do
    SONG=$(tail -n 1 $LOGFILE | cut -f 4 -d '|')
    if [ "$SONG" != "$PREV_SONG" ]
    then
        echo "New song: $SONG"
        redis-cli publish now_playing "$SONG"
        PREV_SONG=$SONG
    fi
    sleep 1
done
