from cogs.utils import ClearQueue
from discord.voice_client import ProcessPlayer
from discord.ext import commands
from subprocess import Popen, PIPE
from threading import Thread, Event
import asyncio
import spotify
import discord
import logging
import shlex
import time
import queue

# logging.setLevel(logging.INFO)
# log = logging.getLogger(__name__)

class DiscordPlayer(Thread):

    def __init__(self, session, bot, loop, voice, playlist):
        Thread.__init__(self)
        self.session = session
        self.bot = bot
        self.loop = loop
        self.voice = voice
        self.playlist = playlist
        self.player = None
        self.current = None
        self.session.on(spotify.SessionEvent.END_OF_TRACK, self._on_end_of_track)
        self.session.on(spotify.SessionEvent.MUSIC_DELIVERY, self._on_music_delivery)
        self._ready = Event()
        self._pause = Event()
        self._end = Event()
        self._skip = Event()
        self.frame_queue = ClearQueue()
        self.end_of_track = Event()

    def run(self):
        self.setup()

    def _on_end_of_track(self, session):
        self.session.player.pause()
        self.end_of_track.set()

    def _on_music_delivery(self, session, audio_format, frames, num_frames):
        self.frame_queue.put_nowait((audio_format.sample_rate, frames, num_frames))
        return num_frames

    def setup(self):
        while not self._end.is_set():
            try:
                self.current = self.playlist.get(timeout=10)

                if not self.current.is_loaded:
                    self.current.load()
                    self.current.artists.load()

                self.session.player.load(self.current)
                self.update_playing(track=self.current)

                timeout_count = 0
                maxrate = "4000k"
                bufsize = "8000k"

                # cmd = "ffmpeg -f s16le -codec:a pcm_s16le -ac 2 -ar 44100 -i - " \
                #       "-f s16le -ar {} -ac {} -maxrate {} -bufsize {}  -loglevel warning pipe:1".format(
                #         self.voice.encoder.sampling_rate,
                #         self.voice.encoder.channels,
                #         maxrate,
                #         bufsize
                # )
                # args = shlex.split(cmd)
                # self.proc = Popen(args, stdin=PIPE, stdout=PIPE)
                # self.player = ProcessPlayer(self.proc, self.voice, None)

                #TODO: Test this
                before = "-f s16le -codec:a pcm_s16le -ac 2 -ar 44100"
                options = "-maxrate {} -bufsize {}".format(maxrate, bufsize)
                self.player = self.voice.create_ffmpeg_player(PIPE, pipe=True, before_options=before, options=options)
                self.proc = self.player.process

                self._ready.set()
                self.session.player.play()
                time.sleep(1)
                self.player.start()

                while not self.frame_queue.empty():
                    try:
                        while self._pause.is_set():
                            if self._end.is_set():
                                self._pause.clear()
                                break
                            else:
                                time.sleep(1)

                        if self._end.is_set() or self._skip.is_set():
                            self.frame_queue.clear()
                            self._skip.clear()
                            break

                        play_item = self.frame_queue.get(timeout=1)

                        if self._ready.is_set():
                            self.proc.stdin.write(play_item[1])

                    except queue.Empty:
                        print("Timeout ", timeout_count)
                        timeout_count += 1
                        if timeout_count > 30:
                            raise spotify.Error("Timeout while playing track.")

            except queue.Empty:
                continue
            except (spotify.Error, Exception) as e:
                if isinstance(e, spotify.Error):
                    print("Spotify error!")
                print(repr(e))
                self.session.player.unload()
                self.cleanup()
                return

        self.cleanup()

    def update_playing(self, track=None):
        if track:
            artists = ", ".join(a.name for a in track.artists)
            song = "{0.name} - {1}".format(track, artists)
            game = discord.Game(name=song)
        else:
            game = discord.Game()

        coro = self.bot.change_status(game=game)
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        try:
            future.result(1)
        except asyncio.TimeoutError:
            future.cancel()
        except Exception as e:
            print(repr(e))

    def playing(self):
        if not self._pause.is_set() or self._end.is_set():
            return True
        else:
            return False

    @property
    def volume(self):
        if self.player:
            return self.player.volume

    @volume.setter
    def volume(self, vol):
        if self.player:
            self.player.volume = vol

    def pause(self):
        self._pause.set()
        self._ready.clear()
        self.player.pause()
        self.update_playing()

    def resume(self):
        if self._pause.is_set():
            self._pause.clear()
            self._ready.set()
            self.player.resume()
            self.update_playing(self.current)

    def skip(self):
        self.session.player.pause()
        self.session.player.unload()
        self._skip.set()

    def stop(self):
        self._end.set()

    def cleanup(self):
        self.session.player.pause()
        self.session.player.unload()

        if self.player:
            self.player.stop()

        time.sleep(1)

        if self.proc:
            try:
                self.proc.stdin.flush()
                self.proc.stdin.close()
            except ValueError:
                pass

            ret = self.proc.wait()

            if ret != 0:
                print("Error occured when trying to close ffmpeg process:", str(ret))

        self.playlist.clear()
        self.session.off(event=spotify.SessionEvent.END_OF_TRACK)
        self.session.off(event=spotify.SessionEvent.MUSIC_DELIVERY)
