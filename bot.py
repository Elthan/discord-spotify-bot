#!/usr/bin/env python3.5

from discord.ext import commands
from cogs.utils import ClearQueue
from cogs import config
from cogs import music
from cogs import search
import asyncio
import discord
import logging
import spotify
import threading

description = '''A bot for playing music from Spotify.'''

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix=config.prefix, description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

# SETUP #
logged_in_event = threading.Event()
def connection_state_listener(session):
    if session.connection.state is spotify.ConnectionState.LOGGED_IN:
        logged_in_event.set()

session = spotify.Session()
loop = spotify.EventLoop(session)
loop.start()
session.on(
    spotify.SessionEvent.CONNECTION_STATE_UPDATED,
    connection_state_listener
)

session.login(config.user, config.secret)

logged_in_event.wait()
print(session.user)
session.preferred_bitrate(spotify.Bitrate.BITRATE_320k)

playlist = ClearQueue()
bot.add_cog(search.Search(bot, session, playlist))
bot.add_cog(music.Music(bot, session, playlist))

bot.run(config.token)
