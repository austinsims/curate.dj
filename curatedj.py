from flask import Flask, url_for, render_template, redirect, request
import redis
import flask
from mpd import MPDClient
import urllib

curatedj = Flask(__name__)
red = redis.StrictRedis()

# Scrape number of listeners from the icecast2 status page.
def population():
    pass

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

def vote_tally_stream():
    pubsub = red.pubsub()
    pubsub.subscribe('vote_tally')
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

@curatedj.route('/vote_tally_stream')
def serve_vote_tally_stream():
    return flask.Response(vote_tally_stream(), mimetype="text/event-stream")

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

        pp = red.get('population')
        if pp is None:
            population = 0
        else:
            population = int(pp)
        population = population + 1

        red.set('population', population)

        con = connect()
        if 'song' in con.status():
            index = int(con.status()['song'])
            song = con.playlistinfo()[index]
            picked = red.get(song['file'])
            vote_tally = red.get('vote_tally')
        else:
            song = None
            picked = None
            vote_tally = 0
        return render_template('index.html', song=song, picked=picked, username=username, vote_tally=vote_tally)

@curatedj.route('/upvote')
def upvote():
    votes = int(red.get('vote_tally'))
    votes = votes + 1
    red.set('vote_tally', votes)
    red.publish('vote_tally', votes)
    return ''

@curatedj.route('/downvote')
def downvote():


    votes = int(red.get('vote_tally'))
    population = int(red.get('population'))
    votes = votes - 1
    red.set('vote_tally', votes)

    #Skip if the song sucks.
#    if votes <= int(math.ceil(float(population) / float(-2))):
    if votes <= -1:
        cl = connect()
        cl.next()
        votes = 0
        red.set('vote_tally',votes)


    red.publish('vote_tally', votes)
    return ''

@curatedj.route('/goodbye/<username>')
def goodbye(username):
    population = int(red.get('population'))
    population = population - 1
    red.set('population', population)
    return redirect(url_for('index'))

@curatedj.route('/add/<path:filepath>', methods=['POST'])
def add(filepath):
    username = request.form['username']
    cl = connect()
    cl.add(filepath)
    red.set(filepath, username)
    song = cl.listallinfo(filepath)[0]
    artist = song['artist']
    title = song['title']
    red.set('vote_tally',0)
    red.publish('vote_tally', red.get('vote_tally'))
    cl.play()
    message = "%s - %s, Picked by: %s" % (artist, title, username)
    return message

@curatedj.route('/countvotes')
def countvotes():
    return red.get('vote_tally')

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
