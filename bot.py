import discord
import firebase_admin
import os
import requests

from datetime import datetime
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from discord import app_commands, Forbidden
from discord.ext import commands

load_dotenv()
TOKEN =  os.getenv('DISCORD_TOKEN')
TMDB = os.getenv('TMDB')
BASE_URL = "https://api.themoviedb.org/3"
GUILD_ID = discord.Object(id=510231690682171415)
ALLOWED_THREAD_ID = 1336754097759588444
ROLE = "KT Max"

# OMDB

# Firebase Connection

cred = credentials.Certificate("C:/Users/mudKI/Downloads/ktcinemabot-2ef82-firebase-adminsdk-fbsvc-5449434d99.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Discord Bot Setup

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

class MovieBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True 
        super().__init__(command_prefix="/", intents=intents)
        self.synced = False  # Track if commands are synced

    async def on_ready(self):
        print(f'✅ Logged in as {self.user}')

        # Force sync commands to the guild
        if not self.synced:
            try:
                guild = GUILD_ID  # Replace with your server ID
                synced = await self.tree.sync(guild=guild)
                self.synced = True  # Prevent re-syncing every time bot restarts
                print(f'✅ Synced {len(synced)} commands to guild {guild.id}')
            except Exception as e:
                print(f'❌ Error syncing commands: {e}')

bot = MovieBot()

# Commands

async def is_valid_thread(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_THREAD_ID:
        await interaction.response.send_message("🚫 This command can only be used in the designated thread!", ephemeral=True)
        return
    return True

# @bot.tree.command(name="movie", description="Usage: /movie <movie_name> <release_date (MM/DD/YYYY)>", guild=GUILD_ID)
# async def movie(interaction: discord.Interaction, movie_name: str, release_date: str = None):

#     if not await is_valid_thread(interaction):
#         return
    
#     movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]
    
#     movie_data = {"name": movie_name, 'release_date': release_date if release_date else None}

#     if release_date:
#         try:
#             parsed_date = datetime.strptime(release_date, "%m/%d/%Y")
#             movie_data["release_date"] = parsed_date
#         except ValueError:
#             await interaction.response.send_message("⚠️ Invalid date format! Use MM/DD/YYYY.", ephemeral=True)
#             return

#     movie_ref = db.collection("watchlist").document(movie_name)
#     movie_ref.set(movie_data)
#     await interaction.response.send_message(f"🎬 '{movie_name}' has been added!")

@bot.tree.command(name="movie", description="Usage: /movie <movie_name>", guild=GUILD_ID)
async def movie(interaction: discord.Interaction, movie_name:str, year: str=""):

    if not await is_valid_thread(interaction):
        return
    
    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]
   
    params = {
        'query': movie_name,  # Use 'query' for TMDb API to search by title
        'year': year,
        "api_key": TMDB,  # TMDB API Key, not OMDB
    }

    response = requests.get(f"{BASE_URL}/search/movie", params=params)
    data = response.json()

    try:
        movie = data["results"][0]
        movie_data = {'title': movie['title'], 'release_date': datetime.strptime(movie['release_date'], "%Y-%m-%d"), 'backdrop_path': movie['backdrop_path']}
        movie_ref = db.collection("movies").document(movie['title'])
        movie_ref.set(movie_data)
        watchlist_ref = db.collection("watchlist").document(movie['title']).set({'movie_ref': movie_ref.path, 'release_date': datetime.strptime(movie['release_date'], "%Y-%m-%d"), 'title':movie['title']})
    except Exception as E:
       await interaction.response.send_message(f"❌ {movie_name} could not be added!")
       return

    await interaction.response.send_message(f"🎬 '{movie_name}' has been added!")

@bot.tree.command(name="moviedel", description="Usage: /moviedel <movie_name>", guild=GUILD_ID)
async def moviedel(interaction: discord.Integration, movie_name: str):

    if not await is_valid_thread(interaction):
        return

    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]

    movie_reference = db.collection("watchlist").document(movie_name)

    try:
        movie_reference.delete()
        await interaction.response.send_message(f"🎬 '{movie_name}' has been deleted from the watchlist!")
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Failed to delete '{movie_name}'. Error: {e}")

@bot.tree.command(name="movielist", description="View the current watchlist", guild=GUILD_ID)
async def movielist(interaction: discord.Interaction):

    if not await is_valid_thread(interaction):
        return
    
    movies = db.collection("watchlist").order_by("release_date").stream()

    movie_list = []
    
    for movie in movies:
        movie_data = movie.to_dict()
        name = movie_data.get("title")
        release_date = movie_data.get("release_date")
        formatted_date = datetime.strftime(release_date, "%m-%d-%Y")
        if release_date is not None:
            if isinstance(release_date, datetime):
                movie_list.append(f"\t\t**{name}** | Released on {formatted_date} \n")
            else:
                movie_list.append(f"\t\t**{name}** | Release date not specified \n")
        else:
            movie_list.append(f"\t\t**{name}** | Release date not specified \n")

    if not movie_list:
        await interaction.response.send_message("📭 No movies added yet!")
    else:
        await interaction.response.send_message(f"🎥 **Movie List:**\n\n" + "\n".join(movie_list))
    
@bot.tree.command(name="moviepoll", description="Usage: /moviepoll <movie_name>", guild=GUILD_ID)
async def moviepoll(interaction: discord.Interaction, movie_name: str):

    if not await is_valid_thread(interaction):
        return
    
    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]

    role = discord.utils.get(interaction.guild.roles, name=ROLE)
    
    if role:
        await interaction.response.send_message(f"Hey {role.mention}, whos down to attend **{movie_name}**! Vote now!")
    else:
        await interaction.response.send_message("❌ The role @KTCinema does not exist.", ephemeral=True)

    message = await interaction.original_response()

    emoji = discord.utils.get(interaction.guild.emojis, name="dapepe")

    if(emoji):
        await message.add_reaction(emoji)
    else:
        await message.add_reaction("👍")

    date_emoji = [
        "🇲",
        "🇹",
        "🇼",
        "⬆️",
        "🇫",
        "🇸",
        "☀️"
    ]

    for date in date_emoji:
        await message.add_reaction(date)

@bot.tree.command(name="clearbot", description="Clear bot messages", guild=GUILD_ID)
async def clearbot(interaction: discord.Interaction):
    if not await is_valid_thread(interaction):
        return

    channel = interaction.channel

    # if(channel.permissions_for(interaction.guild.me).manage_messages):
    #     await interaction.response.send_message("yes")
    # else:
    #     await interaction.response.send_message("no")

    await interaction.response.defer()  

    if not channel.permissions_for(interaction.guild.me).manage_messages:
        await interaction.followup.send("❌ I do not have permission to manage messages in this channel.", ephemeral=True)
        return

    if channel:
        try:
            await channel.purge(limit=50, check=lambda m: m.author == bot.user)
            await interaction.followup.send(f"🗑️ Deleted bot messages!", ephemeral=True)
        except discord.errors.NotFound:
            print("Message not found or already deleted")
            await interaction.followup.send(f"🗑️ Deleted bot messages!", ephemeral=True)
        except Forbidden:
            await interaction.followup.send("❌ I do not have permission to manage messages in this channel.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Could not find the channel.", ephemeral=True)

@bot.tree.command(name="moviereview", description="Usage: /moviereview <movie_name> <rating (int:0-5)>", guild=GUILD_ID)
async def moviereview(interaction: discord.Interaction, movie_name: str, rating: str):
    
    if not await is_valid_thread(interaction):
        return

    try:
        rating = float(rating)
    except:
        await interaction.response.send_message("❌ Rating must be a valid number between 0 and 5.", ephemeral=True)
        return
    
    if(not(0 <= rating <= 5) ):
        await interaction.response.send_message("❌ Rating needs to be a value from 0 to 5!", ephemeral=True)
    
    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]
    rating = round(rating, 1)
    user_review = {"movie_name": movie_name.lower(), "name": movie_name, "rating": float(rating), "reviewed_on": interaction.created_at}
    user_ref = db.collection("users").document(str(interaction.user.id))
    user_doc = user_ref.get()

    if user_doc.exists:
        existing_reviews = user_doc.to_dict().get("reviews", [])
        existing_reviews.append(user_review)
        user_ref.update({"reviews": existing_reviews})
    else:
        user_ref.set({"reviews": [user_review]})

    movie_ref = db.collection("movies").document(str(movie_name).lower())
    movie_doc = movie_ref.get()

    if movie_doc.exists:
        movie_ref.update({"reviewers": firestore.ArrayUnion([str(interaction.user.id)])})
    else:
        movie_ref.set({"reviewers": [str(interaction.user.id)]})

    await interaction.response.send_message(f"💥 {str(interaction.user.name)} has rated '{movie_name}' {str(rating)} 💥!")

@bot.tree.command(name="reviewdelete", description="Usage: /reviewdelete <movie_name>", guild=GUILD_ID)
async def reviewdel(interaction: discord.Interaction, movie_name:str):

    if not await is_valid_thread(interaction):
        return
    
    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]

    user_ref = db.collection("users").document(str(interaction.user.id))
    user_doc = user_ref.get()

    if user_doc.exists:
        reviews = user_doc.to_dict().get("reviews", [])

        for review in reviews:
            if(review["movie_name"] == movie_name.lower()):
                user_ref.update({"reviews": firestore.ArrayRemove([review])})

    movie_ref = db.collection("movies").document(str(movie_name).lower())
    movie_doc = movie_ref.get()

    if movie_doc.exists:
        reviewers = movie_doc.to_dict().get("reviewers", [])
        for reviewer in reviewers:
            if(reviewer == str(interaction.user.id)):
                movie_ref.update({"reviewers": firestore.ArrayRemove([str(interaction.user.id)])})

    await interaction.response.send_message(f"✅ Movie {movie_name}'s review has been deleted!", ephemeral=True)

@bot.tree.command(name="reviewlist", description="Usage: /reviewlist", guild=GUILD_ID)
async def reviewlist(interaction:discord.Interaction):
    user_review = db.collection("users").document(str(interaction.user.id)).get().to_dict().get("reviews", [])
    review_list = f"✏️ {str(interaction.user.name)} Movie Reviews: \n\n"

    for review in user_review:
        boom_string = ""
        for i in range(0, round(float(review["rating"]))):
            boom_string += "💥"
        review_list += f"\t\t {str(review['movie_name']).title()} - {str(review['rating'])} {boom_string}\n\n"

    await interaction.response.send_message(f"{review_list}")

bot.run(TOKEN)