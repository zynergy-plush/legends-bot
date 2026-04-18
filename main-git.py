import discord
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta, timezone

# intents
UTC = timezone.utc
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Store active giveaways
giveaways = {}


# Welcome/goodbye channel storage (guild_id: {'welcome': channel_id, 'goodbye': channel_id})
welcome_channels = {}


# Check if user has admin permissions
def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


# On ready
@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    try:
        synced = await tree.sync()
        print(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'❌ Failed to sync: {e}')


# Help command (public)
@tree.command(name="help", description="📚 Show all bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Bot Commands", description="All available commands:", color=0x0099FF)
    embed.add_field(
        name="🎉 **Giveaways**",
        value="`giveaways` - List active giveaways",
        inline=False
    )

    embed.set_footer(text="You used /help.")
    embed.timestamp = datetime.now(UTC)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Admin‑only help command
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


# Welcome msg
@client.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    if guild_id in welcome_channels and 'welcome' in welcome_channels[guild_id]:
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
    else:
        print(f"DEBUG: Welcome channel not set for guild {guild_id}")


# Goodbye msg
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


# Set welcome channel (Admin only)
@tree.command(name="setwelcome", description="📢 Set welcome channel only (Admin only)")
@app_commands.describe(channel="Channel for welcome messages")
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ **Admin only!**", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    if guild_id not in welcome_channels:
        welcome_channels[guild_id] = {}
    welcome_channels[guild_id]['welcome'] = channel.id
    print(f"DEBUG: Welcome channel set to {channel.id} for guild {guild_id}")
    await interaction.response.send_message(f"✅ Welcome messages set to {channel.mention}", ephemeral=True)


# Set goodbye channel (Admin only)
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


# Send message command
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


# Give away command (admin only)
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


# Ban command
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


# Kick command
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


# Timeout command
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


# Untimeout command
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


# Reroll giveaway winner (Admin only)
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


# Lists active giveaways
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

# Ends a giveaway after a duration
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


# Reaction Handling
@client.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.id not in giveaways or str(reaction.emoji) != '🎉':
        return
    try:
        await reaction.remove(user)
    except:
        pass    

# BOT TOKEN 
client.run('BOT_TOKEN_HERE')