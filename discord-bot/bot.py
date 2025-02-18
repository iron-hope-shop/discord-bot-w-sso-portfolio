# CMD + K CMD + 0 to fold all code blocks, J to unfold
from modules.stonks import (
    calculate_rsi,
    create_stock_chart,
    create_rsi_chart,
    create_stats_table,
    generate_simulated_data,
)
from constants import TEST_ITEMS, STORAGE_BUCKET, SKILL_NAMES, ALLOWED_SERVER_IDS, ALLOWED_CHANNEL_IDS
from modules.ui import Paginator, RSSPaginator
from modules.fun import fetch_player_stats
from config import DISCORD_BOT_TOKEN
from utils import fetch_rss_feed
from discord.ext import commands
from google.cloud import storage
from flask import Flask, request
import os, sys, json
import numpy as np
import threading
import asyncio
import discord
import random
import firebase_admin
from firebase_admin import credentials, auth
import secrets
from urllib.parse import urlencode

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # If you need to read message content
intents.reactions = True  # For reaction events

intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.authenticated_users = {}

storage_client = storage.Client()

# Initialize Firebase app
cred = credentials.Certificate("./svc-account.json")
firebase_admin.initialize_app(cred)

# Dictionary to store temporary auth states
auth_states = {}

app = Flask(__name__)


@app.route("/health")
def health_check():
    return "sit", 200


def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Custom exceptions
class TriviaDMError(commands.CommandError):
    pass

class TriviaServerError(commands.CommandError):
    pass

class TriviaChannelError(commands.CommandError):
    pass

class TriviaInProgressError(commands.CommandError):
    pass

def fetch_trivia_questions():
    blob_name = "bot/trivia_questions.json"

    bucket = storage_client.get_bucket(STORAGE_BUCKET)
    blob = bucket.blob(blob_name)

    json_data = blob.download_as_text()
    questions = json.loads(json_data)
    return questions["questions"]


async def fetch_leaderboard():
    blob_name = "bot/trivia_leaderboard.json"

    bucket = storage_client.get_bucket(STORAGE_BUCKET)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        return {}

    json_data = blob.download_as_text()
    return json.loads(json_data)


async def update_leaderboard(user_name, points=1):
    leaderboard = await fetch_leaderboard()

    if user_name in leaderboard:
        leaderboard[user_name] += points
    else:
        leaderboard[user_name] = points

    blob_name = "bot/trivia_leaderboard.json"

    bucket = storage_client.get_bucket(STORAGE_BUCKET)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(json.dumps(leaderboard))

def cooldown_check(ctx):
    return not isinstance(ctx.channel, discord.DMChannel)

active_trivia_servers = set()

def trivia_check():
    def predicate(ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            raise TriviaDMError()
        if ctx.guild.id not in ALLOWED_SERVER_IDS:
            raise TriviaServerError()
        if ctx.channel.id not in ALLOWED_CHANNEL_IDS:
            raise TriviaChannelError()
        if ctx.guild.id in active_trivia_servers:
            raise TriviaInProgressError()
        return True
    return commands.check(predicate)

@bot.command(name="trivia")
@trivia_check()
async def trivia(ctx):
    if ctx.channel.id == 1259221807832236142:
        try:
            active_trivia_servers.add(ctx.guild.id)

            questions = fetch_trivia_questions()
            question_data = random.choice(questions)
            question = question_data["question"]
            answer = question_data["answer"]
            difficulty = question_data["difficulty"]
            category = question_data["category"]

            embed = discord.Embed(title="RuneScape Trivia", color=0x395262)
            embed.set_thumbnail(url="https://oldschool.runescape.wiki/images/Lumbridge_Guide.png?426c8")
            embed.add_field(name=f"{difficulty} - {category}", value=question, inline=False)
            embed.set_footer(text="You have 30 seconds to answer!")
            await ctx.send(embed=embed)

            def check(m):
                return m.channel == ctx.channel

            end_time = asyncio.get_event_loop().time() + 30.0
            correct_user = None

            while True:
                try:
                    time_left = end_time - asyncio.get_event_loop().time()
                    if time_left <= 0:
                        break

                    user_answer = await bot.wait_for("message", check=check, timeout=time_left)

                    if user_answer.content.lower() == answer.lower():
                        correct_user = user_answer.author
                        break

                except asyncio.TimeoutError:
                    break

            if correct_user:
                await ctx.send(f"Congratulations, {correct_user.mention}! You got the correct answer: {answer}")
                await update_leaderboard(correct_user.display_name)
            else:
                await ctx.send(f"Time's up! The correct answer was: {answer}")

        except Exception as e:
            await ctx.send(f"An error occurred while fetching the trivia question. {e}")
        finally:
            active_trivia_servers.remove(ctx.guild.id)
    else:
        await ctx.send(f"Wrong channel. Please use <#1259221807832236142> for this command.", ephemeral=True)

@trivia.error
async def trivia_error(ctx, error):
    if isinstance(error, TriviaDMError):
        await ctx.send("https://tenor.com/bmcQR.gif")
    elif isinstance(error, TriviaServerError):
        await ctx.send("https://tenor.com/bmcQR.gif")
    elif isinstance(error, TriviaChannelError):
        # You can choose to send a message or silently ignore
        pass
    elif isinstance(error, TriviaInProgressError):
        await ctx.send("A trivia game is already in progress in this server.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
    else:
        print(f"An unexpected error occurred: {error}")
        await ctx.send("An error occurred while running the trivia command.")


# @bot.command(name="trivia_stats")
# async def trivia_stats(ctx):
#     # Placeholder for trivia statistics
#     # You can implement a system to track and display user statistics here
#     await ctx.send("Trivia statistics feature coming soon!")


@bot.command(name="trivia_leaderboard")
async def trivia_leaderboard(ctx):
    try:
        leaderboard = await fetch_leaderboard()

        if not leaderboard:
            await ctx.send("The leaderboard is currently empty.")
            return

        sorted_leaderboard = sorted(
            leaderboard.items(), key=lambda x: x[1], reverse=True
        )

        embed = discord.Embed(title="Trivia Leaderboard", color=0x00FF00)

        for i, (user, score) in enumerate(sorted_leaderboard[:10], start=1):
            embed.add_field(name=f"{i}. {user}", value=f"Score: {score}", inline=False)

        await ctx.send(embed=embed)

    except:
        await ctx.send(f"An error occurred while fetching the leaderboard.")


@bot.command(name="lookup")
async def lookup(ctx, username: str):
    if ctx.channel.id == 1259246684106395658:
        stats = fetch_player_stats(username, skill_names=SKILL_NAMES)
        if not stats:
            await ctx.send(
                f"Could not fetch stats for {username}. Please check the username and try again. If the problem persists, you may not be ranked on the hiscores yet."
            )
            return

        embed = discord.Embed(
            title=f"{username}'s Stats",
            color=0x841A0E,
        )

        # Use the 'Overall' stats directly from the stats dictionary
        overall_level = int(stats["Overall"]["level"])
        overall_xp = int(stats["Overall"]["experience"])

        embed.add_field(
            name="Overall",
            value=f"Level: {overall_level}\nXP: {overall_xp:,}",
            inline=False,
        )
        embed.add_field(
            name="\u200b", value="*Stats are sorted from highest to lowest.*", inline=False
        )
        # Sort stats by experience (descending), excluding 'Overall'
        sorted_stats = sorted(
            [(k, v) for k, v in stats.items() if k != "Overall"],
            key=lambda x: int(x[1]["experience"]),
            reverse=True,
        )

        # Create a single uninterrupted column of stats
        row_text = ""
        for stat, values in sorted_stats:
            level = int(values["level"])
            xp = int(values["experience"])
            skill_name_padded = (stat[:6] + "..").ljust(8, ".")
            skill_display = (
                f"({level:2}) {skill_name_padded}"
                if level == 99
                else f"({level:2}) {skill_name_padded}"
            )
            row_text += f"`{skill_display:<10} {max(xp, 0):11,} XP`\n"

        embed.add_field(name="\u200b", value=row_text, inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send(f"Wrong channel. Please use <#1259246684106395658> for this command.", ephemeral=True)
    


@bot.command(name="stock")
async def stock(ctx):
    time, stock_prices = generate_simulated_data()
    chart_buf = create_stock_chart(time, stock_prices)

    embed = discord.Embed(
        title="📈 Simulated Stock Prices",
        description="Here's a simulated stock price chart with a smaller interval.",
        color=0x00FF00,
    )
    embed.add_field(
        name="Current Price", value=f"${stock_prices[-1]:.2f}", inline=False
    )
    embed.add_field(
        name="Highest Price", value=f"${np.max(stock_prices):.2f}", inline=True
    )
    embed.add_field(
        name="Lowest Price", value=f"${np.min(stock_prices):.2f}", inline=True
    )
    embed.set_image(url="attachment://stock_chart.png")

    await ctx.send(file=discord.File(chart_buf, "stock_chart.png"), embed=embed)


@bot.command(name="stats")
async def stats(ctx):
    time, stock_prices = generate_simulated_data()
    rsi = calculate_rsi(stock_prices)
    stats_table = create_stats_table(stock_prices, rsi)

    chart_buf = create_rsi_chart(time, rsi)

    embed = discord.Embed(
        title="📊 Stock Statistics",
        description="Here are the stock statistics including RSI.",
        color=0x00FF00,
    )
    embed.set_image(url="attachment://rsi_chart.png")

    stats_str = stats_table.to_string(index=False)
    embed.add_field(name="Statistics", value=f"```\n{stats_str}\n```", inline=False)

    await ctx.send(file=discord.File(chart_buf, "rsi_chart.png"), embed=embed)


@bot.command(name="button")
async def button(ctx):
    button = discord.ui.Button(label="Click Me!", style=discord.ButtonStyle.primary)

    async def button_callback(interaction):
        await interaction.response.send_message("Button clicked!")

    button.callback = button_callback

    view = discord.ui.View()
    view.add_item(button)

    await ctx.send("Here's a button:", view=view)


@bot.command(name="dropdown")
async def dropdown(ctx):
    options = [
        discord.SelectOption(label="Option 1", description="This is option 1"),
        discord.SelectOption(label="Option 2", description="This is option 2"),
        discord.SelectOption(label="Option 3", description="This is option 3"),
    ]

    select = discord.ui.Select(placeholder="Choose an option...", options=options)

    async def select_callback(interaction):
        await interaction.response.send_message(f"You selected: {select.values[0]}")

    select.callback = select_callback

    view = discord.ui.View()
    view.add_item(select)

    await ctx.send("Here's a dropdown menu:", view=view)


@bot.command(name="osrss")
async def rsfeed(ctx):
    feed_url = "https://secure.runescape.com/m=news/latest_news.rss"  # Replace with the actual RSS feed URL
    items = fetch_rss_feed(feed_url)
    pages = []

    for item in items:
        embed = discord.Embed(
            title=item.title, url=item.link, description=item.summary, color=0x00FF00
        )
        embed.set_author(name=item.author if "author" in item else "RuneScape")
        embed.set_footer(text=item.published)

        # Check if the item has an enclosure and it's an image
        if "enclosures" in item and item.enclosures:
            for enclosure in item.enclosures:
                if enclosure.type.startswith("image"):
                    embed.set_image(url=enclosure.url)
                    break

        pages.append(embed)

    paginator = RSSPaginator(pages)
    await paginator.send_initial_message(ctx)


@bot.command(name="paginate_items")
async def paginate_items(ctx):
    pages = []
    for item in TEST_ITEMS:
        embed = discord.Embed(title=item["name"], color=0x00FF00)
        embed.set_thumbnail(url=item["image"])
        embed.add_field(name="ID", value=item["id"], inline=True)
        embed.add_field(name="High Alch", value=f"${item['high_alch']}", inline=True)
        embed.add_field(name="Low Alch", value=f"${item['low_alch']}", inline=True)
        embed.add_field(
            name="Current Price", value=f"${item['current_price']}", inline=True
        )
        embed.add_field(name="High Volume", value=item["high_vol"], inline=True)
        embed.add_field(name="Low Volume", value=item["low_vol"], inline=True)
        embed.add_field(name="High Price", value=f"${item['high_price']}", inline=True)
        embed.add_field(name="Low Price", value=f"${item['low_price']}", inline=True)

        # Add empty fields to control the columns
        if len(embed.fields) % 3 != 0:
            for _ in range(3 - (len(embed.fields) % 3)):
                embed.add_field(name="\u200b", value="\u200b", inline=True)

        pages.append(embed)

    paginator = Paginator(pages)
    await paginator.send_initial_message(ctx)


@bot.command(name="paginate")
async def paginate(ctx):
    pages = [
        discord.Embed(title="Page 1", description="This is the first page."),
        discord.Embed(title="Page 2", description="This is the second page."),
        discord.Embed(title="Page 3", description="This is the third page."),
    ]
    paginator = Paginator(pages)
    await paginator.send_initial_message(ctx)

@bot.command(name="login")
async def login(ctx):
    # Generate a unique state for this login attempt
    state = secrets.token_urlsafe(16)
    auth_states[state] = ctx.author.id

    # Construct the Firebase Auth URL
    # Replace 'your-project-id' with your actual Firebase project ID
    auth_url = f"https://osrs-trading-app.web.app/auth?state={state}"

    embed = discord.Embed(
        title="Login to Your Account",
        description="Click the button below to sign into runetick. This link will expire shortly... use !login for a new one.",
        color=discord.Color.blue()
    )

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Login", url=auth_url, style=discord.ButtonStyle.link))

    await ctx.author.send(embed=embed, view=view)

@app.route("/auth_callback")
def auth_callback():
    state = request.args.get("state")
    id_token = request.args.get("id_token")

    if state not in auth_states:
        return "Invalid state", 400

    user_id = auth_states.pop(state)
    
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        name = decoded_token.get('name', 'User')  # Get the user's name from the token

        # Store the user's Firebase UID and name in memory
        bot.authenticated_users[user_id] = {'uid': uid, 'name': name}

        return "Authentication successful! You can close this window and return to Discord."
    except Exception as e:
        print(f"Error verifying token: {e}")
        return "Authentication failed", 400

@bot.command(name="whoami")
async def whoami(ctx):
    user_id = ctx.author.id
    if user_id in bot.authenticated_users:
        name = bot.authenticated_users[user_id]['name']
        await ctx.send(f"You are authenticated as: {name}")
    else:
        await ctx.send("You are not authenticated. Please use the `!login` command to log in.")

# @bot.event
# async def on_raw_reaction_add(payload):
#     if payload.message_id == 1260035899903705158:
#         if str(payload.emoji) == "<:cut_diamond:1260067187855720468>":
#             guild = bot.get_guild(payload.guild_id)
#             member = guild.get_member(payload.user_id)
#             role = guild.get_role(1260031100697182218)
#             await member.add_roles(role)

# @bot.event
# async def on_raw_reaction_remove(payload):
#     if payload.message_id == 1260035899903705158:
#         if str(payload.emoji) == "<:cut_diamond:1260067187855720468>":
#             guild = bot.get_guild(payload.guild_id)
#             member = guild.get_member(payload.user_id)
#             role = guild.get_role(1260031100697182218)
            
#             # Check if the member has only this role (apart from @everyone)
#             if len(member.roles) == 2 and role in member.roles:
#                 await member.remove_roles(role)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(DISCORD_BOT_TOKEN)
