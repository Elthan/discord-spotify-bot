from discord.ext import commands
from cogs.player import DiscordPlayer
from threading import Thread, Event
import asyncio
import discord
import spotify
import queue

if not discord.opus.is_loaded():
    discord.opus.load('opus')

class Music:
    """Plays music from Spotify."""

    def __init__(self, bot, session, playlist):
        self.voice = None
        self.player = None
        self.status_thread = None
        self.skip_votes = set()
        self.bot = bot
        self.session = session
        self.spotify_player = session.player
        self.session.preferred_bitrate(spotify.Bitrate.BITRATE_320k)
        self.playlist = playlist

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx, *, channel : discord.Channel):
        """Joins a voice channel."""
        try:
            self.voice = await self.bot.join_voice_channel(channel)
        except discord.ClientException:
            await self.bot.say("Already in voice channel...")
        except discord.InvalidArgument:
            await self.bot.say("That is not a voice channel...")
        else:
            await self.bot.say("Ready to play in " + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summon the bot to join your channel"""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say("You are not in a voice channel...")
            return

        if not self.voice:
            self.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await self.voice.move_to(summoned_channel)

    @commands.command(no_pm=True)
    async def play(self, link = ""):
        """Start or resume the player. Add a song to queue with a URI/URL or search."""
        if not self.voice:
            await self.bot.say("Need to join channel first!")
            return

        if not self.player:
            self.player = DiscordPlayer(self.session, self.bot, self.bot.loop, self.voice, self.playlist)
            self.player.start()

        if not link:
            if not self.player.playing():
                self.player.resume()
                await self.bot.say("Resumed play.")
                return
            else:
                await self.bot.say("Already playing.")
                return

        try:
            uri = self.session.get_link(link).uri
            track = self.session.get_track(uri).load()
        except ValueError:
            await self.bot.say("Unable to find song from URI/URL.")
            return
        except Exception as e:
            print("Spotify error!")
            print(repr(e))
            return

        if track.availability is not spotify.TrackAvailability.AVAILABLE:
            await self.bot.say("Track is not available for playing.")
            return

        # if self.player.playing():
        await self.bot.say("Track added to queue.")

        self.playlist.put(track)

    @commands.command(no_pm=True)
    async def stop(self):
        """Pauses the currently playing track. Resume with play or resume."""
        if not self.player.playing():
            await self.bot.say("Currently not playing anything...")
            return

        self.player.pause()
        await self.bot.say("Stopped.")

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Pauses the currently playing track."""
        if not self.player.playing():
            await self.bot.say("Currently not playing anything...")
            return

        self.player.pause()
        await self.bot.say("Paused.")

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        """Resumes paused track."""
        if self.player:
            if not self.player.playing():
                self.player.resume()
                await self.bot.say("Resumed play.")
            else:
                await self.bot.say("No track paused.")
        else:
            await self.bot.say("Have not started playing yet...")

    @commands.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        """Leave the voice channel."""
        if not self.bot.is_voice_connected(ctx.message.server):
            await self.bot.say("Currently not connect to a voice channel...")
            return

        if self.player:
            self.player.stop()
            self.player.join()
            self.player = None
            await self.bot.change_status(game=discord.Game())

        try:
            await self.voice.disconnect()
        except Exception as e:
            print("Failed to leave: ", e)

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Votes to skip song. 2 votes are needed to skip."""
        if not self.player.playing():
            await self.bot.say("Currently not playing anything...")
            return

        voter = ctx.message.author
        if voter.id not in self.skip_votes:
            self.skip_votes.add(voter.id)
            cur_votes = len(self.skip_votes)
            if cur_votes >= 2:
                await self.bot.say("Skipping song...")
                self.player.skip()
                self.skip_votes.clear()
            else:
                await self.bot.say("Added vote, currently at {}/2 votes.".format(cur_votes))
        else:
            await self.bot.say("You have already voted to skip this song.")

    @commands.command(pass_context=True, no_pm=True, description="Valid volume is between 0 and 200. Only permitted users can do this.")
    async def volume(self, ctx, vol = ""):
        """Get the current volume or set the volume."""
        print("Roles:", ctx.message.author.roles)

        if self.player:
            if not self.player.playing():
                await self.bot.say("Currently not playing anything...")
                return
        else:
            await self.bot.say("Currently not playing anything...")
            return

        if not vol:
            await self.bot.say("Current volume is " + str(self.player.volume))
            return

        set_vol = min(max(float(vol) / 100.0, 0.0), 2.0)

        #TODO: Check permissions
        self.player.volume = set_vol

        await self.bot.say("Volume adjusted to {}.".format(str(set_vol)))
