from __future__ import annotations

from shutil import which
from os.path import join
from os import pathsep, environ

class Endpoints:
    def __init__(self):
        self.home = "https://music.apple.com"
        self.amp = "https://amp-api.music.apple.com/v1/catalog/{region}/{type}/{id}"
        self.playback = "https://play.music.apple.com/WebObjects/MZPlay.woa/wa/webPlayback"
        # self.playlist = "https://amp-api.music.apple.com/v1/catalog/{region}/albums/{playlist_id}?l=en-us&platform=web&omit[resource]=autos&include=tracks,artists&include[songs]=artists,composers&extend[url]=f"

class Folders:
    def __init__(self):
        self.binaries = "binaries"
        self.cookies = "cookies"
        self.temp = "temp"
        self.output = "output"

folder = Folders()
# Add binaries folder to PATH as the first item
environ['PATH'] = pathsep.join([folder.binaries, environ['PATH']])

class Binaries:
    def __init__(self):
        self.mp4decrypt = which("mp4decrypt")
        self.mkvmerge = which("mkvmerge")
        self.shaka = which("packager")
        self.ffmpeg = which("ffmpeg")
        self.aria2c = which("aria2c")

class Filenames:
    def __init__(self):
        self.base_track_video = '{filename}_{track_type}_{track_no}_'
        self.base_track_audio = '{filename}_{track_type}_{track_no}_'
        self.base_video_muxed = '{filename}.mkv'
        self.base_audio_muxed = '{filename}.m4a'
        self.musics_template = '{track} - {artist} - {name}'
        self.videos_template = '{artist} - {name}'
        self.encrypted_filename_video = join(folder.temp, self.base_track_video + 'encrypted.mp4')
        self.decrypted_filename_video = join(folder.temp, self.base_track_video + 'decrypted.mp4')
        self.encrypted_filename_audio = join(folder.temp, self.base_track_audio + 'encrypted.m4a')
        self.decrypted_filename_audio = join(folder.temp, self.base_track_audio + 'decrypted.m4a')
        self.decrypted_filename_audio_ff = join(folder.temp, self.base_track_audio + 'decrypted_fixed.m4a')
        self.muxed_video_filename = join(folder.output, '{filename}.mkv')
        self.muxed_audio_filename = join(folder.output, '{filename}.m4a')


binaries = Binaries()
endpoints = Endpoints()
filenames = Filenames()