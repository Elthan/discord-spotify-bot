from discord.ext import commands
import discord
import spotify

class Search:

    def __init__(self, bot, session, playlist):
        self.bot = bot
        self.session = session
        self.playlist = playlist
        self.searching = set()
        self.to_del = []

    def is_int(self, x):
        try:
            int(x)
            return True
        except ValueError:
            return False

    async def print_results(self, tracks):
        results = "```"

        results += "Name | Artist | Album\n"
        for idx, track in list(enumerate(tracks, start=1)):
            try:
                track.load()
            except spotify.LibError as lb:
                await self.bot.say("Encountered an error.")
                print(lb.error_type)
                return
            else:
                by = ", ".join(a.name for a in track.artists)
                results += "{0}: {1.name} | {2} | {1.album.name}\n".format(str(idx), track, by)

        return await self.bot.say(results+ "```")

    @commands.command(description="Prefix with title:, artist: or album: to narrow the search.", pass_context=True)
    async def search(self, ctx, *args : str):
        """Search Spotify. See help search for tips."""
        await self.bot.type()

        self.to_del.append(ctx.message)
        self.author = ctx.message.author
        if self.author.id in self.searching:
            await self.bot.say("You are already searching, please cancel your search before searching again.")
            return
        else:
            self.searching.add(self.author.id)

        if len(args) == 0:
            sent_msg = await self.bot.say("What to search for? (Type cancel to cancel)")
            self.to_del.append(sent_msg)
            msg = await self.bot.wait_for_message(author=self.author, channel=ctx.message.channel, timeout=30)

            if msg is None:
                return await self.done("Timed out")

            self.to_del.append(msg)

            if msg.content.lower() == "cancel":
                return await self.done("Search cancelled.")
            else:
                search_args = msg.content
        else:
            search_args = str(args)

        try:
            res = self.session.search(search_args, track_count=10).load()
        except spotify.LibError as lb:
            print(lb.error_type)
            return await self.done("Encountered an error.")

        if not res.tracks:
            return await self.done("Found no more results.")

        sent_msg = await self.print_results(res.tracks)
        self.to_del.append(sent_msg)

        while True:
            sent_msg = await self.bot.say("*more* for more results, *play <index>* or *<index>* to add to queue, *cancel* to cancel.")
            self.to_del.append(sent_msg)

            check = lambda msg: msg.content.lower().startswith(("more", "play", "cancel")) or self.is_int(msg.content.lower())
            msg = await self.bot.wait_for_message(author = self.author,
                                                  channel = ctx.message.channel,
                                                  timeout = 30,
                                                  check = check)

            if msg is None:
                return await self.done("Timed out.")

            self.to_del.append(msg)

            if "cancel" in msg.content.lower():
                return await self.done("Search cancelled.")

            if "more" in msg.content.lower():
                try:
                    res = res.more().load()
                except spotify.LibError as lb:
                    print(lb.error_type)
                    return await self.done("Encountered an error.")
                if not res.tracks:
                    return await self.done("Found no more results.")
                sent_msg = await self.print_results(res.tracks)
                self.to_del.append(sent_msg)
            elif "play" in msg.content.lower() or isinstance(int(msg.content), int):
                try:
                    idx = int(msg.content.split()[1]) if "play" in msg.content.lower() else int(msg.content)
                    idx -= 1
                    try:
                        track = res.tracks[idx]
                    except IndexError:
                        sent_msg = await self.bot.say("Invalid index, please select a valid index:")
                        self.to_del.append(sent_msg)
                        msg = await self.bot.wait_for_message(author = ctx.message.author,
                                                              channel = ctx.message.channel,
                                                              timeout = 30)
                        self.to_del.append(msg)
                        idx = int(msg.content.split()[1]) if "play" in msg.content.lower() else int(msg.content)
                        idx -= 1
                        track = res.tracks[idx]
                except (ValueError, IndexError):
                    return await self.done("Invalid index.")

                if not track.is_loaded:
                    try:
                        track.load()
                    except spotify.LibError as lb:
                        print(lb.error_type)
                        return await self.done("Encountered an error.")

                await self.bot.say(track.link.uri)
                self.playlist.put(track)

                return await self.done("Track added to queue.")
            else:
                continue

    async def done(self, msg):
        await self.bot.say(msg)
        self.searching.remove(self.author.id)
        await self.bot.delete_messages(self.to_del)
        return
