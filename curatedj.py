from flask import Flask, url_for, render_template, redirect, request
import redis
import flask
from mpd import MPDClient

curatedj = Flask(__name__)
red = redis.StrictRedis()

def song_title_stream():
    pubsub = red.pubsub()
    pubsub.subscribe('now_playing')
    # TODO: handle client disconnection.
    for message in pubsub.listen():
        print message
        yield 'data: %s\n\n' % message['data']

def position_stream():
    pubsub = red.pubsub()
    pubsub.subscribe('position')
    for message in pubsub.listen():
        print message
        yield 'data: %s\n\n' % message['data']

def connect():
    cl = MPDClient()
    cl.connect("localhost", 6600)
    return cl

def unknown_album(artist):
    '''
    Find songs without an album by the given artist
    '''
    cl = connect()
    result = list()
    for song in cl.find('album',''):
        if 'artist' in song and song['artist'] == artist:
            result.append(song)
    return result

@curatedj.route('/song_title_stream')
def serve_song_title_stream():
    return flask.Response(song_title_stream(), mimetype="text/event-stream")

@curatedj.route('/position_stream')
def serve_position_stream():
    return flask.Response(position_stream(), mimetype="text/event-stream")

@curatedj.route('/playlist')
def playlist():
    cl = connect()
    playlist = cl.playlistinfo()
    state = cl.status()['state']
    if state == 'play':
        playing_index = int(cl.status()['song'])
        playlist[playing_index]['playing'] = True
        
    return render_template('playlist.html', playlist=playlist)

@curatedj.route('/', methods=['GET','POST'])
def index():

    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form['username']

        con = connect()
        if 'song' in con.status():

            index = int(con.status()['song'])
            song = con.playlistinfo()[index]
            picked = red.get(song['file'])
        else:
            song = None
            picked = None
        return render_template('index.html', song=song, picked=picked, username=username)



@curatedj.route('/add/<path:filepath>', methods=['POST'])
def add(filepath):
    username = request.form['username']
    cl = connect()
    cl.add(filepath)
    # TODO: store "who added me" info with playlist--need to store
    # playlist somewhere else beside inside python-mpd2 library??
    # write wrapper for playlist functions??
    red.set(filepath, username)
    cl.play()
    return request.form['username']

@curatedj.route('/browse')
@curatedj.route('/browse/<artist>')
@curatedj.route('/browse/<artist>/<album>')
def browse(artist=None, album=None):
    cl = connect()
    if artist is None:
        artists = sorted(cl.list('artist'))
        return render_template('list_artists.html', artists=artists)
    elif album is None:
        albums = cl.list('album', artist)
        return render_template('list_albums.html', artist=artist, albums=albums, other=unknown_album(artist))
    else:
        songs = cl.find('album', album)
        return render_template('list_songs.html', songs=songs, album=album)

if __name__ == '__main__':
    curatedj.debug = True
    curatedj.run(host='0.0.0.0', port=80)
