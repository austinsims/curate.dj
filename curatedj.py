from flask import Flask, url_for, render_template, redirect
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
        if song['artist'] == artist:
            result.append(song)
    return result

@curatedj.route('/song_title_stream')
def serve_song_title_stream():
    return flask.Response(song_title_stream(), mimetype="text/event-stream")

@curatedj.route('/playlist')
def playlist():
    cl = connect()
    playlist = cl.playlistinfo()
    return render_template('playlist.html', playlist=playlist)

@curatedj.route('/')
def index():
    con = connect()
    try:
        index = int(con.status()['song'])
    except KeyError:
        song = None
    song = con.playlistinfo()[index]
    return render_template('index.html', song=song)

@curatedj.route('/next')
def next():
    cl = connect()
    cl.next()
    return redirect(url_for('playlist'))

@curatedj.route('/prev')
def prev():
    cl = connect()
    cl.previous()
    return redirect(url_for('playlist'))

@curatedj.route('/add/<path:filepath>')
def add(filepath):
    cl = connect()
    cl.add(filepath)
    cl.play()
    return redirect(url_for('index'))

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
