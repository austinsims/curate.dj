#!/bin/bash

# Monitor the currently playing song in Icecast and send a redis
# notification to the 'now_playing' channel when it changes.

# Usage: monitor.sh /path/to/playlist.log

function position_message {

    # Only do something if a song is playing.
    SONG=$(mpc current)
    if [ "$SONG" != "" ]
    then
	TIME=$(mpc status|tail -n 2 | head -n 1 | cut -d ' ' -f 5)
	PCT=$(mpc status|tail -n 2 | head -n 1 | cut -d ' ' -f 6)
	echo $TIME
	redis-cli publish position "{\"time\":\"$TIME\", \"percentage\":\"$PCT\"}"
    fi
    
}

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
	# Send new song message and zero-second message
        echo "New song: $SONG"
        redis-cli publish now_playing "$SONG"
        PREV_SONG=$SONG
	echo "RESETTING VOTES"
	redis-cli set vote_tally 0
	position_message
    else
	position_message
    fi
    sleep 1
done
