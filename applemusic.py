from __future__ import annotations

import os
import re
import sys
import time
import json
import m3u8
import base64
import shutil
import urllib3
import requests
import argparse
import music_tag
import webbrowser
import subprocess
import unicodedata
import pathvalidate

import config as toolcfg

from unidecode import unidecode
from urllib.parse import unquote
from subprocess import CalledProcessError
from coloredlogs import ColoredFormatter, logging
from pywidevine.L3.decrypt.wvdecrypt import WvDecrypt
from pywidevine.L3.decrypt.wvdecryptconfig import WvDecryptConfig
from pywidevine.L3.cdm.formats.widevine_pssh_data_pb2 import WidevinePsshData
from colorama import init

REGEX = re.compile(r"//music\.apple\.com/.*/(?P<type>.*)/(?P<name>.*)/(?P<id>\d*)[\?i=]*(?P<track_id>\d*)?$")


init(autoreset=True)

BANNER = """
    ___                __        __  ___           _         ____  _                      
   /   |  ____  ____  / /__     /  |/  /_  _______(_)____   / __ \(_)___  ____  ___  _____
  / /| | / __ \/ __ \/ / _ \   / /|_/ / / / / ___/ / ___/  / /_/ / / __ \/ __ \/ _ \/ ___/
 / ___ |/ /_/ / /_/ / /  __/  / /  / / /_/ (__  ) / /__   / _, _/ / /_/ / /_/ /  __/ /    
/_/  |_/ .___/ .___/_/\___/  /_/  /_/\__,_/____/_/\___/  /_/ |_/_/ .___/ .___/\___/_/     
      /_/   /_/                                                 /_/   /_/                                                         

> REMAKE By ReiDoBregaBR
> SOURCE By Puyodead1
> VERSION 2.0.0
"""
class VideoTrack:

    def __init__(self, type_, url, uri, aid, audio_only):
        self.type = type_
        self.url = url
        self.uri = uri
        self.aid = aid
        self.audio_only = audio_only

    def get_type(self):
        return 'video'

    def get_filename(self, unformatted_filename):
        return unformatted_filename.format(filename=self.filename, track_type='video', track_no='0')

class AudioTrack:

    def __init__(self, type_, url, uri, aid, audio_only):
        self.type = type_
        self.url = url
        self.uri = uri
        self.aid = aid
        self.audio_only = audio_only

    def get_type(self):
        return 'audio'

    def get_filename(self, unformatted_filename):
        return unformatted_filename.format(filename=self.filename, track_type='audio', track_no='0')

def checkIfInt(str):
    try:
        x = int(str)
        return x
    except ValueError:
        return

def checkIfBoolean(str):
    try:
        x = int(str)
        if x in [0,1]:
            if x == 0:
                return False
            elif x == 1:
                return True
        else:
            return
    except ValueError:
        aslower = str.lower()
        if aslower in ['yes','on','true']:
            return True
        elif aslower in ['no','off','false']:
            return False
        else:
            return

class Bunch(object):
    def __init__(self, adict, bdict):
        def handledict(anydict):
            newdict = {}
            for idx, name in enumerate(list(anydict.keys())):
                newname = name.replace('-','_')
                newdict[newname] = list(anydict.values())[idx]
            return newdict
        newadict = handledict(adict)
        for item in newadict:
            if item in ['skip_cleanup','debug','keys']:
                bool = checkIfBoolean(newadict[item])
                if bool is not None:
                    newadict[item] = bool
                else:
                    print(f'ERROR: Config param {item!r} has to be boolean value')
                    sys.exit(2)
            if item in ['title', 'track','track_start']:
                int = checkIfInt(newadict[item])
                if int is not None:
                    newadict[item] = int
                else:
                    print(f'ERROR: Config param {item!r} has to be int value')
                    sys.exit(2)
        newbdict = handledict(bdict)
        self.__dict__.update(newadict)
        #~ print(self.__dict__)
        for item in newbdict:
            if item not in self.__dict__:
                self.__dict__[item] = newbdict[item]
            elif newbdict[item] != None and newbdict[item] != False:
                self.__dict__[item] = newbdict[item]

class AppleMusicClient:

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.args = args
        self.args.url = self._title(args.url)
        self.session = self.client_session()        
        self.audio_only = True if self.content_type != 'music-video' else False
        self.contents_to_be_ripped = []

    def _title(self, title):
        matches = re.search(REGEX, title)
        if not matches:
            try:
                self.url_track_id = None
                self.content_type = 'album'
                if 'playlist' in title:
                    self.content_type = 'playlist'
                elif '?i=' in title:
                    self.content_type = 'track'
                args.url = title.split('/')[-1]
            except:
                self.log.fatal("[-] Invalid URL..")
                exit(1)
            return args.url

        self.content_type = matches.group(1)
        self.url_name = matches.group(2)
        self.url_main_id = matches.group(3)
        self.url_track_id = matches.group(4)

        try:
            if self.content_type == "album" and self.url_track_id:
                args.url = self.url_track_id
            elif self.content_type == "album":
                args.url = self.url_main_id
            elif self.content_type == "music-video":
                args.url = self.url_main_id
            else:
                self.log.fatal("[-] Invalid URL: Only Songs, Albums, and Music Videos are supported")
        except Exception as e:
            self.log.exception(f"[-] Error: {e}")
        
        return args.url

    def cookies_(self):
        cookies = {}
        APPLE_MUSIC_COOKIES = os.path.join(toolcfg.folder.cookies, 'cookies.txt')
        if os.path.exists(APPLE_MUSIC_COOKIES) and os.path.isfile(APPLE_MUSIC_COOKIES):
            with open(APPLE_MUSIC_COOKIES, "r") as f:
                for l in f:
                    if not re.match(r"^#", l) and not re.match(r"^\n", l):
                        line_fields = l.strip().replace('&quot;', '"').split('\t')
                        cookies[line_fields[5]] = line_fields[6]
        else:
            self.log.info(f"[+] Vistit {toolcfg.endpoints.home} And Export Cookies From Your Account and Put in Folder..")
            self.log.info("[+] After Add The Cookies, Back To Window And Press Enter")
            time.sleep(5)
            webbrowser.open(toolcfg.endpoints.home)
            input("continue ?")
            return self.cookies_()
        return cookies

    def client_session(self):
        self.session = requests.Session()
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0"})
        self.session.cookies.update(self.cookies_())

        token_file = os.path.join(toolcfg.folder.cookies, 'token.txt')
        if not os.path.exists(token_file) or not os.path.isfile(token_file):
            token = re.search(r'"token":"(.+?)"', unquote(self.session.get(toolcfg.endpoints.home).content.decode()))
            if token:
                token = token.group(1)
                with open(token_file, "w") as f:
                    f.write(token)
        else:
            with open(token_file, "r") as f:
                token = f.read().strip()

        if not token:
            self.log.fatal("[-] Couldn't Find Token From The Homepage, Cookies May Be Invalid.")
            exit(1)

        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "x-apple-music-user-token": self.session.cookies.get_dict()["media-user-token"],
            "x-apple-renewal": "true",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        })
        return self.session

    # Album Music/Single Track
    def fetch_music_metadata(self, track_id):

        data = self.fetch_metadata(track_id)

        music = data["songList"][0]

        song_assets = next((x for x in music["assets"] if x["flavor"] == "28:ctrp256"), None)
        if not song_assets:
            raise Exception("Failed to find 28:ctrp256 asset")
        metadata = song_assets["metadata"]
        metadata['playback'] = song_assets["URL"]
        metadata['artworkURL'] = song_assets["artworkURL"]
        metadata['license'] = music["hls-key-server-url"]

        output_name = toolcfg.filenames.musics_template.format(
            track=metadata['trackNumber'],
            artist=metadata['artistName'],
            name=metadata['itemName']
        )    
        return metadata, output_name

    # Album Music Check
    def fetch_metadata(self, track_id=None):
        data = {
            'salableAdamId': args.url if not track_id else track_id 
        }
        reqs = self.session.post(toolcfg.endpoints.playback, data=json.dumps(data))
        if reqs.status_code != 200:
            self.log.fatal(f"[{reqs.status_code}] {reqs.reason}: {reqs.content}")
            return None
        reqs_js = reqs.json()
        return reqs_js

    def fetch_info(self, type: str, tid=None):
        tid = args.url if not tid else tid
        reqs = self.session.get(toolcfg.endpoints.amp.format(
            type=type, id=tid, region=self.args.region))
        if reqs.status_code != 200:
            self.log.fatal(f"[{reqs.status_code}] {reqs.reason}: {reqs.content}")
            return None
        return reqs.json()
    
    def music_tag(self, data: dict):
        f = music_tag.load_file(self.oufn)
        for key, value in data.items():
            f[key] = value
        f.save()
        shutil.move(self.oufn, self.oufn.replace(
            toolcfg.folder.output, self.album_folder))

    def insert_metadata(self, metadata):
        self.log.info("+ Adding metadata")

        data = {
            "album": metadata["playlistName"],
            "albumartist": metadata["artistName"],
            "artist": metadata["artistName"],
            "comment": metadata["copyright"],
            "compilation": metadata["compilation"],
            "composer": metadata["composerName"],
            "discnumber": metadata["discNumber"],
            "genre": metadata["genre"],
            "totaldiscs": metadata["discCount"],
            "totaltracks": metadata["trackCount"],
            "tracknumber": metadata["trackNumber"],
            "tracktitle": metadata["itemName"],
            "year": metadata["year"],
        }
        # sometimes don't found
        try:
            data['isrc'] = metadata["xid"]
        except KeyError:
            pass

        reqs = requests.get(metadata["artworkURL"])
        if reqs.ok:
            data["artwork"] = reqs.content
        else:
            self.log.warning("- Failed to Get Artwork")

        try:
            self.music_tag(data)
        except Exception as e:
            self.log.warning(f"- Failed to Tag File: {e}")

    def extract_playlist_data(self, metadata):
        playlist = m3u8.load(metadata['playback'])
        if self.content_type != 'music-video':
            fn = playlist.segments[0].uri
            track_url = playlist.base_uri + fn
            key_id = playlist.keys[0].uri
            return track_url, key_id

        # return only audio track url and key id
        track_url = [
            x for x in playlist.media if x.type == "AUDIO"][-1].uri
        key_id = next(x for x in m3u8.load(track_url).keys if x.keyformat ==
                            "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed").uri
        if not key_id:
            self.log.fatal("- Failed To Find Audio Key ID With Widevine SystemID")
            exit(1)

        # for video track -> self only
        self.vt_url = playlist.playlists[-1].uri
        self.vt_kid = next(x for x in  m3u8.load(self.vt_url).keys if x.keyformat ==
                            "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed").uri
        if not self.vt_kid:
            self.log.fatal("- Failed To Find Video Key ID With Widevine SystemID")
            exit(1)
        return track_url, key_id

    def do_ffmpeg_fix(self, track):
        ffmpeg_command = [
            toolcfg.binaries.ffmpeg,
            '-y',
            '-hide_banner',
            '-loglevel', 'error',
            '-i', track,
            '-map_metadata', '-1',
            '-fflags', 'bitexact',
            '-c', 'copy',
            self.oufn,
        ]
        subprocess.run(ffmpeg_command, check=True)

    def download_track(self, tracks: VideoTrack): # KEKE DW
        
        aria2c_input = ''

        for i, track in enumerate(tracks):
            self.log.info("+ Downloading {} Track".format(track.get_type().title()))
            # Music Only
            if self.content_type != 'music-video':
                track_fname = toolcfg.filenames.encrypted_filename_audio.format(
                                    filename=self.filename, track_type=track.type, track_no='0')
                (dname, fname) = os.path.split(track_fname)

                aria2c_input += f'{track.url}\n'
                aria2c_input += f'\tdir={dname}\n'
                aria2c_input += f'\tout={fname}\n'

                aria2c_infile = os.path.join(toolcfg.folder.temp, 'aria2c_infile.txt')
                track_fname = os.path.join(track_fname)
                with open(aria2c_infile, 'w') as fd:
                    fd.write(aria2c_input)
                
                aria2c_opts = [
                    toolcfg.binaries.aria2c,
                    '--allow-overwrite', 'false',
                    '--quiet', 'true', # false
                    '--continue', 'true',
                    '--summary-interval=0',
                    '--async-dns=false',
                    '--disable-ipv6=true',
                    '--retry-wait=5',
                    '-x', '16',
                    '-s', '16',
                    '-i', aria2c_infile,
                ]
                
                try:
                    subprocess.run(aria2c_opts, check=True)
                except CalledProcessError as e:
                    if e.returncode == 13:
                        self.log.info('- File Already Downloaded, not Overwriting')
                    else:
                        if e.returncode == 9:
                            self.log.error('- The Human Controlling the Downloader is Stupid... VERY VERY STUPID LOL...')
                        else:
                            self.log.error(f'I Think Aria2c is Having Some Trouble... it Returned Exit Code {e.returncode}')
                        sys.exit(1)
                os.remove(aria2c_infile)
            else:
                # Music Video
                if track.get_type() == 'video':
                    fname = toolcfg.filenames.encrypted_filename_video.format(
                                        filename=self.filename, track_type=track.get_type(), track_no='0')
                elif track.get_type() == 'audio':
                    fname = toolcfg.filenames.encrypted_filename_audio.format(
                                        filename=self.filename, track_type=track.get_type(), track_no='0')
                self.download_alternative(track.url, fname)

    def download_alternative(self, url: str, output_name: str):
        subprocess.Popen(["yt-dlp", "--allow-unplayable", "-o", output_name, url]).wait()

    def do_service_certificate(self, track: VideoTrack): # KEKE DW
        license_response = self.session.post(
            url=self.license_url,
            data=json.dumps({
                'adamId': track.aid,
                'challenge': "CAQ=",
                'isLibrary': False,
                'key-system': 'com.widevine.alpha',
                'uri': track.uri,
                'user-initiated': True
            }))
        if license_response.status_code != 200:
            self.log.fatal(
                f"[{license_response.status_code}] {license_response.reason}: {license_response.content}")
            sys.exit(1)
        license_response_json = license_response.json()
        if not "license" in license_response_json:
            self.log.fatal("Invalid license response")
            self.log.fatal(license_response_json)
            sys.exit(1)
        return license_response_json["license"]

    def get_license(self, challenge, track: VideoTrack): # KEKE DW
        license_response = self.session.post(
            url=self.license_url,
            data=json.dumps({
                'challenge': challenge,
                'key-system': 'com.widevine.alpha',
                'uri': track.uri,
                'adamId': track.aid,
                'isLibrary': False,
                'user-initiated': True
            }))
        if license_response.status_code != 200:
            self.log.fatal(
                f"[{license_response.status_code}] {license_response.reason}: {license_response.content}")
            sys.exit(1)
        license_response_json = license_response.json()
        if not "license" in license_response_json:
            self.log.fatal("- Invalid license response")
            self.log.fatal(license_response_json)
            sys.exit(1)
        license_b64 = license_response_json["license"]
        return license_b64

    def do_decrypt(self, config: WvDecryptConfig, track: VideoTrack): # KEKE DW
        self.log.info("+ Fetching Service Certificate...")
        cert_data_b64 = self.do_service_certificate(track)
        if not cert_data_b64:
            raise Exception("Failed to get service certificate")
        self.log.info("+ Requesting license...")

      
        if self.content_type != 'music-video':
            wvpsshdata = WidevinePsshData()
            wvpsshdata.algorithm = 1
            wvpsshdata.key_id.append(base64.b64decode(config.init_data_b64.split(",")[1]))
            config.init_data_b64 = base64.b64encode(wvpsshdata.SerializeToString()).decode("utf8")
            self.log.debug(f'init_data_b64: {config.init_data_b64}')
        else:
            config.init_data_b64 = config.init_data_b64.split(",")[1]

        wvdecrypt = WvDecrypt(config)
        chal = base64.b64encode(wvdecrypt.get_challenge()).decode('utf-8')
        license_b64 = self.get_license(chal, track)
        if not license_b64:
            print('NO license')
            return False
        wvdecrypt.update_license(license_b64)
        key = wvdecrypt.start_process()
        return True, key

    def do_merge(self, ats, vfn, output):
        self.log.info("+ Muxing Video + Audio Using MKVMerge")
        mkvmerge_command = [toolcfg.binaries.mkvmerge,
                            "--output",
                            output,
                            "--no-date",
                            "--language",
                            "0:und",
                            "(",
                            vfn,
                            ")",
                            "--language",
                            "0:und",
                            "(",
                            ats,
                            ")"]
        subprocess.run(mkvmerge_command)

    def fetch_titles(self):
        self.log.info('+ Starting Apple Music Ripper')
        # album music/ single track/ playlists
        if self.content_type in ('album', 'playlist'):
            # No Single Track, Download Full Album
            if not self.url_track_id:
                album_info = self.fetch_info(
                    ("albums" if self.content_type == 'album' else 'playlists'))
                if not album_info:
                    raise Exception("Failed to get album info")
                    
                self.album_name =  normalize(album_info["data"][0]["attributes"]["name"])

                tracks = album_info["data"][0]["relationships"]["tracks"]["data"]

                if args.track:
                    try:
                        if ',' in args.track:
                            tracks_list = [int(x) for x in args.track.split(',')]
                        elif '-' in args.track:
                            (start, end) = args.track.split('-')
                            tracks_list = list(range(int(start), int(end) + 1))
                        else:
                            tracks_list = [int(args.track)]
                    except ValueError:
                        print('ERROR: track must be either a single number (ex: 1), '
                                'a range (ex: 2-5) or a comma-separated list of values (ex: 1,3,4)')
                        sys.exit(1)
                    try:
                        eplist = []
                        for num, ep in enumerate(tracks_list, 1):
                            eplist.append(tracks[int(ep) - 1])
                            tracks_list = eplist
                    except IndexError:
                        self.log.error(
                            'The requested track ({}) was not found.'.format(args.track))
                        sys.exit(1)
                else:
                    tracks_list = tracks
                    
                if args.track_start:
                    tracks_list = tracks_list[(int(args.track_start) - 1):]
            else:
                # Single Track
                tracks_list = []
                tracks_single = {
                    'id': self.url_track_id
                }
                tracks_list.append(tracks_single)

            for track in tracks_list:
                metadata, output_name = self.fetch_music_metadata(track["id"])
                output_name = normalize(output_name)
                self.contents_to_be_ripped.append((metadata, output_name))
        # music video
        elif self.content_type == 'music-video':
            video_info = self.fetch_info("music-videos", tid=self.url_main_id)
            if not video_info:
                raise Exception("Failed to Get Video Info")

            # hls here
            data = self.fetch_metadata(self.url_main_id)
            try:
                video_ls = data["songList"][0]
            except KeyError:
                self.log.error(data['customerMessage'])
                sys.exit(1)

            metadata = video_info["data"][0]["attributes"]
            metadata['playback'] = video_ls["hls-playlist-url"]
            metadata['license'] = video_ls["hls-key-server-url"]
            metadata['itemId'] = self.url_main_id

            output_name = toolcfg.filenames.videos_template.format(
                artist=metadata['artistName'],
                name=metadata['name']
            )
            output_name = normalize(output_name)
            self.contents_to_be_ripped.append((metadata, output_name))

        return self.contents_to_be_ripped
        
    def run(self, metadata, filename):

        self.filename = filename
        self.log.info(f'+ Downloading {filename}..')
        track_url, track_uri = self.extract_playlist_data(metadata)
        self.license_url = metadata['license']
        # Mount Object AudioTrack + "VideoTrack" if Music Video..
        ats = AudioTrack(type_='audio', url=track_url, uri=track_uri, aid=metadata['itemId'], audio_only=self.audio_only)
        enc_tracks = [ats]
        if self.content_type == 'music-video':
            # make video track
            vts = VideoTrack(type_='video', url=self.vt_url, uri=self.vt_kid, aid=metadata['itemId'], audio_only=False)
            enc_tracks += [vts]

        if not self.args.keys:
            # Download Tracks
            self.download_track(enc_tracks)
        for track in enc_tracks:
            # Decrypt
            self.log.info("+ Decrypting {} Track".format(track.type.title()))
            wvdecrypt_config = WvDecryptConfig(self.args, self.content_type ,self.filename, track.get_type(), track.audio_only,
                                                '0', self.args.keys, track_uri, cert_data_b64=None)
            success, key = self.do_decrypt(wvdecrypt_config, track)
        if self.args.keys:
            return
        else:
            self.log.info("+ All Decrypting Complete")
            if self.content_type != 'music-video':
                self.album_folder = os.path.join(toolcfg.folder.output, self.album_name)
                if not os.path.exists(self.album_folder):
                    os.mkdir(self.album_folder)

                ffmpeg_atrack = wvdecrypt_config.get_filename(toolcfg.filenames.decrypted_filename_audio_ff)
                self.oufn = wvdecrypt_config.get_filename(toolcfg.filenames.muxed_audio_filename)
                self.do_ffmpeg_fix(ffmpeg_atrack)
                # Music Tag
                self.insert_metadata(metadata)
            else:
                ats = toolcfg.filenames.decrypted_filename_audio.format(
                                    filename=self.filename, track_type='audio', track_no='0')
                vts = toolcfg.filenames.decrypted_filename_video.format(
                                    filename=self.filename, track_type='video', track_no='0')
                out = wvdecrypt_config.get_filename(toolcfg.filenames.muxed_video_filename)
                self.do_merge(ats, vts, out)

        if self.args.skip_cleanup:
            self.log.info('+ Skipping Clean')
            return True
        self.log.info("+ Cleaning Temporary Files")
        file_list = [f for f in os.listdir(toolcfg.folder.temp)]
        for f in file_list:
            if f.startswith("{}".format(self.filename)):
                os.remove(os.path.join(toolcfg.folder.temp,f))
        return True


def unwanted_char(asin):
    nfkd_form = unicodedata.normalize('NFKD', asin)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode("utf-8")

def normalize(outputfile):
    outputfile = unwanted_char(outputfile)
    outputfile = pathvalidate.sanitize_filename(outputfile)
    outputfile = unidecode(outputfile)
    outputfile = re.sub(r'[]!"#$%\'()*+,:;<=>?@\\^_-`|~[]', '', outputfile)
    outputfile = re.sub(r'\.{2,}', '.', outputfile)

    return outputfile

if __name__ == "__main__":

    print(BANNER)

    parser = argparse.ArgumentParser(
        description='Apple Music Ripper')

    parser.add_argument('url', nargs='?', help='apple music title url')
    parser.add_argument('-t', '--track', help='rip only specified track from album')
    parser.add_argument('-ts', '--track_start', help="rip starting at the track number provided")
    parser.add_argument('-r', '--region', default='us', choices=['us', 'eu', 'br'], help='Apple Music Region')
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    # don't use with music video, bad fps lol
    parser.add_argument("-m4", "--mp4decrypt", dest="mp4_decrypt", action="store_true",
                        help="Use mp4decrypt instead of shaka-packager to decrypt files")
    parser.add_argument('-k', '--skip-cleanup', action='store_true', help='skip cleanup step')
    parser.add_argument("--keys", action="store_true", help="show keys and exit")
    args_parsed = parser.parse_args()

    config_dict = {}
    args = Bunch(config_dict, vars(args_parsed))

    DEBUG_LEVELKEY_NUM = 21
    logging.addLevelName(DEBUG_LEVELKEY_NUM, "LOGKEY")

    def logkey(self, message, *args, **kws):
        # Yes, logger takes its '*args' as 'args'.
        if self.isEnabledFor(DEBUG_LEVELKEY_NUM):
            self._log(DEBUG_LEVELKEY_NUM, message, args, **kws)

    logging.Logger.logkey = logkey

    logger = logging.getLogger()
        
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = ColoredFormatter(
        '[%(asctime)s] %(levelname)s: %(message)s', datefmt='%I:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if args.keys:
        logger.setLevel(21)
    else:
        logger.setLevel(logging.INFO)

    if args.debug:
        logger.setLevel(logging.DEBUG)

    client = AppleMusicClient()
    titles = client.fetch_titles()
    for metadata, filename in titles:
        if args.keys:
            logger.logkey('{}'.format(filename))
        client.run(metadata, filename)