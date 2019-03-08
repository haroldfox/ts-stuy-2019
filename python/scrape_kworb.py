from bs4 import BeautifulSoup
import numpy as np
import os.path
import pandas as pd
import urllib.request

def read_url(url):
    with urllib.request.urlopen(url) as fp:
        mybytes = fp.read()
        mystr = mybytes.decode("utf8")
    return mystr

def read_song(track_name, url):
    full_url = url.replace('..', 'https://kworb.net/spotify/')
    track_text = read_url(full_url)
    soup = BeautifulSoup(track_text, 'html.parser')
    div = soup.find('div', **{'class': 'weekly'})
    data = {'Date': [], 'Streams': []}
    song_artist_data = {'Artist': [], 'ArtistLink': []}
    for i, tr in enumerate(div.find_all('tr')):
        if i >= 3:
            tds = tr.find_all('td')
            dt = tds[0].string
            if len(tds) > 3:
                streams = tds[2].find(**{'class': 's'})
            else:
                streams = tds[1].find(**{'class': 's'})
            data['Date'].append(pd.Timestamp(dt))
            if streams is not None:
                data['Streams'].append(np.float64(streams.string.replace(',', '')))
            else:
                data['Streams'].append(np.nan)
    for a in soup.find_all('a'):
        if a.has_attr('href'):
            if '../artist' in a['href']:
                song_artist_data['Artist'].append(a.string)
                song_artist_data['ArtistLink'].append(a['href'])
                
    song_df = pd.DataFrame(data)
    song_df['Streams'] = pd.to_numeric(song_df['Streams'])
    song_artist_df = pd.DataFrame(song_artist_data)
    song_df['TrackUrl'] = url
    song_df['Track'] = track_name
    song_artist_df['Track'] = track_name
    song_artist_df['TrackUrl'] = url
    return (song_df, song_artist_df)

def read_top_songs():
    songs_text = read_url('https://kworb.net/spotify/country/us_weekly_totals.html')
    soup = BeautifulSoup(songs_text, 'html.parser')
    top_songs = pd.DataFrame({'Artist': [], 'ArtistLink': [], 'Song': [], 'SongLink': []})
    data = {'Artist': [], 'ArtistLink': [], 'Song': [], 'SongLink': []}
    for table in soup.find_all('tbody'):
    #    print(table)
        for j, row in enumerate(table.find_all('tr')):
            if j < 10:
                print(row)
            aname = ''
            alink = ''
            sname = ''
            slink = ''
            for div in row.find_all('div'):
                if div is not None:
                    links = div.find_all('a')
                    if len(links) == 2:
                        for i, a in enumerate(links):
                            name = a.string
                            if name is None:
                                name = ''
                            link = a['href']
                            if i == 0:
                                aname = name
                                alink = link
                            else:
                                sname = name
                                slink = link
                        if aname is None or alink is None or sname is None or slink is None or len(aname) > 1000 or len(alink) > 1000 or len(sname) > 1000 or len(slink) > 1000:
                            print(div)
                        data['Artist'].append(aname)
                        data['ArtistLink'].append(alink)
                        data['Song'].append(sname)
                        data['SongLink'].append(slink)
    top_songs = pd.DataFrame(data)
    return top_songs
    
if __name__ == '__main__':
    if os.path.exists('songs.h5'):
        top_songs = pd.read_hdf('songs.h5')
    else:
        top_songs = read_top_songs()
        print('read {} songs'.format(top_songs.shape))
#        top_songs['SongLen'] = top_songs['Song'].str.len()
#        top_songs['SongLinkLen'] = top_songs['SongLink'].str.len()
#        top_songs.sort_values('SongLen', ascending=False)
#        top_songs.sort_values('SongLinkLen', ascending=False)
        print(top_songs.tail(10))
        top_songs.copy().to_hdf('songs.h5', 'x', format='table')
    all_songs_df = None
    all_artists_df = None
    if os.path.exists('song_date.h5'):
        all_songs_df = pd.read_hdf('song_date.h5')
    if os.path.exists('song_artist.h5'):
        all_artists_df = pd.read_hdf('song_artist.h5')
        existing_songs = set(all_artists_df['TrackUrl'])
    else:
        existing_songs = set()
    print('existing songs is {}'.format(existing_songs))
    count = 0
    for (_, row) in top_songs.iterrows():
        if row['SongLink'] not in existing_songs:
            print('reading {} {}'.format(row['Song'], row['SongLink']))
            (song_df, artist_df) = read_song(row['Song'], row['SongLink'])
            if all_artists_df is None:
                all_artists_df = artist_df
            else:
                all_artists_df = pd.concat([all_artists_df, artist_df])
            if all_songs_df is None:
                all_songs_df = song_df
            else:
                all_songs_df = pd.concat([all_songs_df, song_df])
            all_songs_df.to_hdf('song_date.h5', 'x', format='table')
            all_artists_df.to_hdf('song_artist.h5', 'x', format='table')
            count += 1