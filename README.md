# Spotify Discord Bot

Using a spotify account to play music in Discord.

## DEPRECATION
This is not maintained and haven't been since I first wrote it in 2016 and unfortunately does not work in its current form (not that it was working great when it was working).   
There has been several changes and libspotify is officially deprecated (though might still work) which means fixing it would 
take more time than I have at the moment.    
You are more than welcome to fork it and I would be happy to point to it from here if you get it working.


## Requirements

- discord.py@async
- pyspotify
- Python 3.5.1+


## Notes

You need a Spotify Premium account to use this bot. This bot is mainly made for
playing music in on one server for friends and has not been tested against anything
else. It is unlikely that it will.

It's not a perfect bot, so expect to have to restart it from time to time.

If you queue something up before it has started to play, you will have to issue
a play command afterwards.


## Installation
Fill in the config.py. Token is the discord token. You also need pyspotify and a Spotify appkey, follow the instructions for this in https://pyspotify.mopidy.com/
