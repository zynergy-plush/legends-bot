# PACKAGES #
import discord
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta, timezone
import yt_dlp
import ffmpeg
from typing import Optional
from discord import VoiceClient

#Global Vars

UTC = timezone.utc
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


giveaways = {}
welcome_channels = {}
voice_clients: dict[int, VoiceClient] = {}
music_queues: dict[int, list] = {} 
current_songs: dict[int, dict] = {} 

# Helper function to check admin permissions
def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


# On Ready MSG on Console
@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    try:
        synced = await tree.sync()
        print(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'❌ Failed to sync: {e}')

# MISC COMMANDS #

# Help command
@tree.command(name="help", description="📚 Show all bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Bot Commands", description="All available commands:", color=0x0099FF)
    embed.add_field(
        name="🎉 **Giveaways**",
        value="`giveaways` - List active giveaways",
        inline=False
    )
    embed.add_field(
        name="🎵 **Music**",
        value="`play` - Play/add to queue\n`queue` - Show queue\n`skip` - Skip\n`pause` - Pause\n`resume` - Resume\n`stop` - Stop\n`clear` - Clear queue",
        inline=False
    )
    embed.add_field(
        name="🙋🏻‍♂️ **help**",
        value="`help` - Show all bot commands",
        inline=False
    )

    embed.set_footer(text="You used /help.")
    embed.timestamp = datetime.now(UTC)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Admin commands
@tree.command(name="adminhelp", description="🛡️ Show admin‑only commands")
async def adminhelp(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ **Admin only!**", ephemeral=True)
        return

    embed = discord.Embed(title="🛡️ Admin‑Only Commands", color=0xFF6600)
    embed.add_field(
        name="🎉 **Giveaways**",
        value="`giveaway` - Start a giveaway\n`reroll` - Reroll a winner\n`giveaways` - List active giveaways",
        inline=False
    )
    embed.add_field(
        name="👋 **Welcome / Goodbye**",
        value="`setwelcome` - Set welcome channel\n`setgoodbye` - Set goodbye channel",
        inline=False
    )
    embed.add_field(
        name="📢 **Messaging**",
        value="`sendmsg` - Send plain text message as bot",
        inline=False
    )
    embed.add_field(
        name="🔨 **Moderation Commands**",
        value="`ban` - Ban member\n`kick` - Kick member\n`timeout` - Timeout member\n`untimeout` - Remove timeout",
        inline=False
    )
    embed.set_footer(text="You used /adminhelp.")
    embed.timestamp = datetime.now(UTC)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Welcome and Goodbye messages
@client.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    if guild_id in welcome_channels:
        if 'welcome' in welcome_channels[guild_id]:
            channel_id = welcome_channels[guild_id]['welcome']
            channel = member.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="👋 Welcome!",
                    description=f"**{member.mention}** joined the server! 👋🏻. We have reached **{member.guild.member_count}** members!",
                    color=0x00FF00
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.timestamp = datetime.now(UTC)
                await channel.send(embed=embed)
                print(f"DEBUG: Welcome sent to {channel.name}")
            else:
                print(f"DEBUG: Welcome channel {channel_id} not found")

        if 'welcome_role' in welcome_channels[guild_id]:
            role_id = welcome_channels[guild_id]['welcome_role']
            role = member.guild.get_role(role_id)
            if role is not None:
                try:
                    await member.add_roles(role)
                    print(f"DEBUG: Role {role.name} given to {member}")
                except discord.Forbidden:
                    print("DEBUG: Cannot give role (missing permissions).")

@client.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    if guild_id in welcome_channels and 'goodbye' in welcome_channels[guild_id]:
        channel_id = welcome_channels[guild_id]['goodbye']
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="👋 Goodbye!",
                description=f"**{member.name}** left the server. 🫡",
                color=0xFF0000
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.timestamp = datetime.now(UTC)
            await channel.send(embed=embed)
            print(f"DEBUG: Goodbye sent to {channel.name}")
        else:
            print(f"DEBUG: Goodbye channel {channel_id} not found")
    else:
        print(f"DEBUG: Goodbye channel not set for guild {guild_id}")

# Set Welcome and Goodbye channels
@tree.command(name="setwelcome", description="📢 Set welcome channel and optional role on join (Admin only)")
@app_commands.describe(
    channel="Channel for welcome messages",
    role="Optional role to give to new members when they join"
)
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role = None):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ **Admin only!**", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in welcome_channels:
        welcome_channels[guild_id] = {}

    welcome_channels[guild_id]['welcome'] = channel.id
    if role is not None:
        welcome_channels[guild_id]['welcome_role'] = role.id
    else:
        welcome_channels[guild_id].pop('welcome_role', None)

    print(f"DEBUG: Welcome channel set to {channel.id} for guild {guild_id}")
    if role:
        await interaction.response.send_message(
            f"✅ Welcome messages set to {channel.mention} and new members will get role {role.mention}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"✅ Welcome messages set to {channel.mention}, no role will be given on join",
            ephemeral=True
        )

@tree.command(name="setgoodbye", description="📢 Set goodbye channel only (Admin only)")
@app_commands.describe(channel="Channel for goodbye messages")
async def setgoodbye(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ **Admin only!**", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    if guild_id not in welcome_channels:
        welcome_channels[guild_id] = {}
    welcome_channels[guild_id]['goodbye'] = channel.id
    print(f"DEBUG: Goodbye channel set to {channel.id} for guild {guild_id}")
    await interaction.response.send_message(f"✅ Goodbye messages set to {channel.mention}", ephemeral=True)

# TROLL COMMAND: Sends message as a bot to any channel (Admin only)
@tree.command(name="sendmsg", description="📢 Send a plain text message as the bot (Admin only)")
@app_commands.describe(channel="Channel to send message", message="Message content")
async def sendmsg(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ **Admin only!**", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        await channel.send(message) 
        await interaction.followup.send(f"✅ **Message sent to {channel.mention}!**", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ **Error sending message:** {str(e)}", ephemeral=True)

# MUSIC COMMANDS #

# Queue command

@tree.command(name="queue", description="📋 Show music queue")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    
    if guild_id not in music_queues or not music_queues[guild_id]:
        await interaction.response.send_message("📭 **Queue is empty!**", ephemeral=True)
        return
    
    embed = discord.Embed(title="🎵 Music Queue", color=0x0099FF)
    
    # Current song
    if guild_id in current_songs:
        current = current_songs[guild_id]
        embed.add_field(
            name="▶️ **Now Playing**",
            value=f"**{current.get('title', 'Unknown')}**",
            inline=False
        )
    
    # Queue list
    queue_list = ""
    for i, song in enumerate(music_queues[guild_id][:10], 1):  # Show top 10
        queue_list += f"{i}. **{song.get('title', 'Unknown')}**\n"
    
    embed.add_field(
        name="⏳ **Queue**",
        value=queue_list or "Empty",
        inline=False
    )
    
    if len(music_queues[guild_id]) > 10:
        embed.set_footer(text=f"And {len(music_queues[guild_id]) - 10} more...")
    
    embed.timestamp = datetime.now(UTC)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# Play command
@tree.command(name="play", description="🎵 Play music (adds to queue if playing)")
@app_commands.describe(query="YouTube URL or search term")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    if not interaction.user.voice:
        await interaction.followup.send("❌ **Join a voice channel first!**", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    voice_channel = interaction.user.voice.channel
    
    # Initialize queue if doesn't exist
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    if guild_id not in current_songs:
        current_songs[guild_id] = None
    
    # Get song info
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'source_address': '0.0.0.0',
        'default_search': 'ytsearch1:',
    }
    
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None, 
            lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(query, download=False)
        )
        
        song_info = {
            'title': info.get('title', 'Unknown'),
            'url': info['url'] if 'url' in info else info['formats'][0]['url'],
            'duration': info.get('duration', 0)
        }
        
        # If nothing playing or queue empty, play immediately
        if guild_id not in voice_clients or not voice_clients[guild_id].is_playing():
            # Connect if needed
            if guild_id not in voice_clients:
                vc = await voice_channel.connect(timeout=15.0, reconnect=True, self_deaf=True)
                voice_clients[guild_id] = vc
            
            current_songs[guild_id] = song_info
            music_queues[guild_id].append(song_info)  # Add to queue too
            
            source = discord.FFmpegPCMAudio(
                song_info['url'],
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn -loglevel quiet"
            )
            
            def after_playing_next(error):
                if error:
                    print(f"Player error: {error}")
                play_next(guild_id)
            
            voice_clients[guild_id].play(source, after=after_playing_next)
            
            embed = discord.Embed(title="▶️ **Now Playing**", description=f"**{song_info['title']}**", color=0x00FF00)
            await interaction.edit_original_response(embed=embed)
            
        else:
            # Add to queue
            music_queues[guild_id].append(song_info)
            embed = discord.Embed(
                title="➕ **Added to Queue**", 
                description=f"**{song_info['title']}** (#{len(music_queues[guild_id])})",
                color=0xFFD700
            )
            await interaction.edit_original_response(embed=embed)
            
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ **Error:** {str(e)}")

# Next song function
async def play_next(guild_id: int):
    if guild_id not in music_queues or not music_queues[guild_id]:
        return
    
    if guild_id not in voice_clients:
        return
    
    next_song = music_queues[guild_id].pop(0)  # Remove first song
    current_songs[guild_id] = next_song
    
    source = discord.FFmpegPCMAudio(
        next_song['url'],
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        options="-vn -loglevel quiet"
    )
    
    def after_next(error):
        if error:
            print(f"Next song error: {error}")
        asyncio.create_task(play_next(guild_id))
    
    voice_clients[guild_id].play(source, after=after_next)

# Pause command
@tree.command(name="pause", description="⏸️ Pause music")
async def pause(interaction: discord.Interaction):
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
        await interaction.response.send_message("❌ **Nothing is playing!**", ephemeral=True)
        return
    
    interaction.guild.voice_client.pause()
    await interaction.response.send_message("⏸️ **Paused!**", ephemeral=True)


# Resume command
@tree.command(name="resume", description="▶️ Resume music")
async def resume(interaction: discord.Interaction):
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_paused():
        await interaction.response.send_message("❌ **Nothing is paused!**", ephemeral=True)
        return
    
    interaction.guild.voice_client.resume()
    await interaction.response.send_message("▶️ **Resumed!**", ephemeral=True)

# Stop command
@tree.command(name="stop", description="⏹️ Stop music and disconnect")
async def stop(interaction: discord.Interaction):
    if not interaction.guild.voice_client:
        await interaction.response.send_message("❌ **Nothing is playing!**", ephemeral=True)
        return
    
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("⏹️ **Stopped and disconnected!**")

# Skip Command
@tree.command(name="skip", description="⏭️ Skip current song")
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in voice_clients or not voice_clients[guild_id].is_playing():
        await interaction.response.send_message("❌ **Nothing is playing!**", ephemeral=True)
        return
    
    voice_clients[guild_id].stop()
    await interaction.response.send_message("⏭️ **Skipped!**")

# Clear Command
@tree.command(name="clear", description="🗑️ Clear music queue")
async def clear(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    music_queues[guild_id] = []
    if guild_id in current_songs:
        current_songs[guild_id] = None
    await interaction.response.send_message("🗑️ **Queue cleared!**")

# MODERATION COMMANDS #

# Ban Command
@tree.command(name="ban", description="🔨 Ban a member")
@app_commands.describe(member="Member to ban", reason="Ban reason")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await interaction.response.defer()
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ Cannot ban higher/equal role!", ephemeral=True)
        return
    await member.ban(reason=reason)
    embed = discord.Embed(title="🔨 Banned", description=f"{member.mention} banned\n**Reason:** {reason}", color=0xFF0000, timestamp=datetime.now(UTC))
    await interaction.followup.send(embed=embed)


# Kick Command
@tree.command(name="kick", description="👢 Kick a member")
@app_commands.describe(member="Member to kick", reason="Kick reason")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await interaction.response.defer()
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ Cannot kick higher/equal role!", ephemeral=True)
        return
    await member.kick(reason=reason)
    embed = discord.Embed(title="👢 Kicked", description=f"{member.mention} kicked\n**Reason:** {reason}", color=0xFF9900, timestamp=datetime.now(UTC))
    await interaction.followup.send(embed=embed)


# Timeout Command
@tree.command(name="timeout", description="⏰ Timeout a member")
@app_commands.describe(
    member="Member to timeout",
    duration="Duration: 1m, 1h, 1d, 7d",
    reason="Timeout reason"
)
@app_commands.choices(duration=[
    app_commands.Choice(name="1 minute", value="1m"),
    app_commands.Choice(name="5 minutes", value="5m"),
    app_commands.Choice(name="1 hour", value="1h"),
    app_commands.Choice(name="1 day", value="1d"),
    app_commands.Choice(name="7 days", value="7d")
])
async def timeout_cmd(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason provided"):
    await interaction.response.defer()
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ Cannot timeout higher/equal role!", ephemeral=True)
        return
    
    duration_seconds = parse_duration(duration)
    if duration_seconds is None or duration_seconds > 604800:
        await interaction.followup.send("❌ **Invalid duration!** Max 7 days", ephemeral=True)
        return
    
    end_time = datetime.now(UTC) + timedelta(seconds=duration_seconds)
    await member.timeout(end_time, reason=reason)
    
    embed = discord.Embed(
        title="⏰ Timed Out",
        description=f"{member.mention} timed out for **{duration}**\n**Reason:** {reason}",
        color=0xFFAA00,
        timestamp=datetime.now(UTC)
    )
    await interaction.followup.send(embed=embed)


# Untimeout Command
@tree.command(name="untimeout", description="✅ Remove timeout")
@app_commands.describe(member="Member to untimeout")
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ Cannot untimeout higher/equal role!", ephemeral=True)
        return
    await member.timeout(None)
    embed = discord.Embed(title="✅ Untimed Out", description=f"{member.mention} timeout removed", color=0x00FF00, timestamp=datetime.now(UTC))
    await interaction.followup.send(embed=embed)

#       GIVEAWAY COMMANDS       #

# Giveaway command
@tree.command(name="giveaway", description="🎉 Start a giveaway! (Admin only)")
@app_commands.describe(
    duration="Duration: 1s, 5m, 1h, 1d",
    prize="What to give away?"
)
@app_commands.choices(duration=[
    app_commands.Choice(name="30 seconds", value="30s"),
    app_commands.Choice(name="1 minute", value="1m"),
    app_commands.Choice(name="5 minutes", value="5m"),
    app_commands.Choice(name="10 minutes", value="10m"),
    app_commands.Choice(name="30 minutes", value="30m"),
    app_commands.Choice(name="1 hour", value="1h"),
    app_commands.Choice(name="6 hours", value="6h"),
    app_commands.Choice(name="1 day", value="1d")
])
async def giveaway(interaction: discord.Interaction, duration: str, prize: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ **Admin only!**", ephemeral=True)
        return

    await interaction.response.defer()

    duration_seconds = parse_duration(duration)
    if duration_seconds is None:
        await interaction.followup.send("❌ **Invalid duration!** Use: 1s, 5m, 1h, 1d", ephemeral=True)
        return

    now = datetime.now(UTC)
    end_time = now + timedelta(seconds=duration_seconds)

    embed = discord.Embed(
        title="🎉 GIVEAWAY STARTED! 🎉",
        description=f"**{prize}**\n\n⏰ **{duration}**\n📅 **Ends:** <t:{int(end_time.timestamp())}:R>",
        color=0xFFD700
    )
    embed.set_footer(text="🎉 React below to ENTER!")
    embed.timestamp = now

    giveaway_msg = await interaction.channel.send(embed=embed)
    await giveaway_msg.add_reaction("🎉")

    giveaway_id = giveaway_msg.id
    giveaways[giveaway_id] = {
        'channel': interaction.channel,
        'end_time': end_time,
        'prize': prize,
        'host': interaction.user,
        'message': giveaway_msg,
        'participants': set()
    }

    asyncio.create_task(end_giveaway_after(giveaway_id, duration_seconds))
    await interaction.followup.send(f"🎉 **Giveaway created!** Ends in `{duration}`")

# giveawy reroll command
@tree.command(name="reroll", description="🎲 Reroll a giveaway winner (Admin only)")
@app_commands.describe(message_id="Message ID of giveaway embed")
async def reroll(interaction: discord.Interaction, message_id: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ **Admin only!**", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        msg_id = int(message_id)
        if msg_id not in giveaways:
            await interaction.followup.send("❌ **Giveaway not found!** Use `/giveaway` first.", ephemeral=True)
            return

        giveaway = giveaways[msg_id]
        message = giveaway['message']

        reaction = None
        for react in message.reactions:
            if str(react.emoji) == '🎉':
                reaction = react
                break

        if not reaction or reaction.count < 2:
            await interaction.followup.send("❌ **No participants to reroll!**", ephemeral=True)
            return

        users = [user async for user in reaction.users() if not user.bot]
        if len(users) < 2:
            await interaction.followup.send("❌ **Need 2+ participants for reroll!**", ephemeral=True)
            return

        winner = random.choice(users)
        embed = discord.Embed(
            title="🎉 REROLLED WINNER! 🎉",
            description=f"**{giveaway['prize']}**\n\n🏆 **{winner.mention}** (Reroll)\n👑 **Rerolled by:** {interaction.user.mention}",
            color=0x00FF00
        )
        embed.timestamp = datetime.now(UTC)
        await message.edit(embed=embed)

        await interaction.followup.send(f"🎉 **Rerolled!** {winner.mention} is new winner!")

    except ValueError:
        await interaction.followup.send("❌ **Invalid message ID!** Right‑click giveaway → Copy ID", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ **Error:** {str(e)}", ephemeral=True)

# giveaway list command
@tree.command(name="giveaways", description="📋 List active giveaways")
async def list_giveaways(interaction: discord.Interaction):
    if not giveaways:
        await interaction.response.send_message("📭 **No active giveaways!**", ephemeral=True)
        return
    
    embed = discord.Embed(title="🎉 Active Giveaways", color=0x0099FF)
    now = datetime.now(UTC)
    for gid, data in giveaways.items():
        time_left = max(0, int((data['end_time'] - now).total_seconds()))
        embed.add_field(
            name=f"**{data['prize']}**",
            value=f"<t:{int(data['end_time'].timestamp())}:R> | {data['host'].mention}",
            inline=False
        )
    
    embed.timestamp = now
    await interaction.response.send_message(embed=embed, ephemeral=True)

def parse_duration(duration_str: str) -> int:
    unit = duration_str[-1].lower()
    try:
        amount = int(duration_str[:-1])
        return {
            's': amount, 'm': amount*60, 'h': amount*3600, 'd': amount*86400
        }[unit]
    except:
        return None

async def end_giveaway_after(giveaway_id: int, duration: int):
    await asyncio.sleep(duration)
    await pick_winner(giveaway_id)

async def pick_winner(giveaway_id: int):
    if giveaway_id not in giveaways:
        return
    
    giveaway = giveaways[giveaway_id]
    message = giveaway['message']
    
    try:
        reaction = next((r for r in message.reactions if str(r.emoji) == '🎉'), None)
        if not reaction or reaction.count < 2:
            embed = discord.Embed(title="😢 NO WINNER", description="Not enough participants!", color=0xFF0000)
            embed.timestamp = datetime.now(UTC)
            await message.edit(embed=embed)
            del giveaways[giveaway_id]
            return
        
        users = [user async for user in reaction.users() if not user.bot]
        winner = random.choice(users)
        
        embed = discord.Embed(
            title="🎉 WINNER SELECTED! 🎉",
            description=f"**{giveaway['prize']}**\n\n🏆 **{winner.mention}**\n👤 **Hosted by:** {giveaway['host'].mention}",
            color=0x00FF00
        )
        embed.timestamp = datetime.now(UTC)
        await message.edit(embed=embed)
        
        await giveaway['channel'].send(f"🎉 **{winner.mention} won {giveaway['prize']}**! DM {giveaway['host'].mention}")
        del giveaways[giveaway_id]
        
    except Exception as e:
        print(f"Giveaway {giveaway_id} error: {e}")

# Reaction handler
@client.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.id not in giveaways or str(reaction.emoji) != '🎉':
        return
    try:
        await reaction.remove(user)
    except:
        pass    

client.run('YOUR-BOT-TOKEN-HERE')