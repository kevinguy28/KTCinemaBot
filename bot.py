import discord
import firebase_admin
import os
import requests
import asyncio

from datetime import datetime
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from discord import app_commands, Forbidden
from discord.ext import commands
from discord.utils import get

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
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

class MovieBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True 
        intents.members = True
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

@bot.event
async def on_member_join(member):
    await member.guild.chunk()  # Ensure the guild's cache is updated

@bot.tree.command(name="movie", description="Usage: /movie <movie_name> [year_of_movie_release]", guild=GUILD_ID)
async def movie(interaction: discord.Interaction, movie_name:str, year: int = None):

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
        movie_title = movie['title']
        movie_data = {'title': movie['title'], 'release_date': datetime.strptime(movie['release_date'], "%Y-%m-%d"), 'backdrop_path': movie['backdrop_path']}
        movie_ref = db.collection("movies").document(movie['title'])
        movie_ref.set(movie_data)
        watchlist_ref = db.collection("watchlist").document(movie['title']).set({'movie_ref': movie_ref.path, 'release_date': datetime.strptime(movie['release_date'], "%Y-%m-%d"), 'title':movie['title']})
    except Exception as E:
       await interaction.response.send_message(f"❌ {movie_name} could not be added!", ephemeral=True)
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
        await interaction.response.send_message(f"🎬 '{movie_title}' has been added! \n\n 🎥 Updated **Movie List:**\n\n" + "\n".join(movie_list))

@bot.tree.command(name="moviedel", description="Usage: /moviedel <movie_name>", guild=GUILD_ID)
async def moviedel(interaction: discord.Integration, movie_name: str):

    if not await is_valid_thread(interaction):
        return

    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]

    movie_reference = db.collection("watchlist").document(movie_name)

    try:
        movie_reference.delete()
        await interaction.response.send_message(f"🎬 '{movie_name}' has been deleted from the watchlist!",  ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to delete '{movie_name}'. Error: {e}",  ephemeral=True)

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
        embed = discord.Embed(title="Jumping Jamanes Watchlist 🎥", description=(f"-----------------------------------------------\n" + "\n".join(movie_list)))
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="moviepoll", description="Usage: /moviepoll", guild=GUILD_ID)
async def moviepoll(interaction: discord.Interaction):
    if not await is_valid_thread(interaction):
        return

    movies = db.collection("watchlist").order_by("release_date").stream()
    movie_list = []
    movie_option = "-----------------------------------------------\n\n"

    for index, movie in enumerate(movies, start=0):
        movie = movie.to_dict()
        movie_list.append(movie)
        movie_option += (f'\t {index} - {movie["title"]} \n\n')

    await interaction.response.send_message("Poll Command Received!", ephemeral=True)

    embed = discord.Embed(title="Which movie should be polled?", description=movie_option)

    og_message = await interaction.channel.send(embed=embed)

    def check(message):
        return message.author == interaction.user and message.channel == interaction.channel
    
    try:
        message = await bot.wait_for('message', check=check, timeout=60.0)
        movie_choice = int(message.content)
        if(movie_choice >= len(movie_list)): await interaction.followup.send("❌ The value you submitted is not a valid input.")
        await og_message.delete()
        await message.delete()
        role = discord.utils.get(interaction.guild.roles, name=ROLE)

        embed = discord.Embed(title=movie_list[movie_choice]['title'], 
                              
                              description= (f"Hey {role.mention}, whos down to attend **{movie_list[movie_choice]['title']}**! Vote now!"),
                              color=discord.Color.red())
        
        url_ref = db.collection('movies').document(movie_list[movie_choice]['title'])
        url = url_ref.get().to_dict().get('backdrop_path')
        url = "https://image.tmdb.org/t/p/w1280" + url
        embed.set_thumbnail(url=url)
        message = await interaction.channel.send(embed=embed)

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

    except ValueError:
        await interaction.response.send_message("❌ Please submit a valid integer for the movie selection.", ephemeral=True)
        await og_message.delete()
    except asyncio.TimeoutError:
        await interaction.response.send_message("❌ You took too long to respond. Please try again.", ephemeral=True)
        await og_message.delete()

@bot.tree.command(name="clearbot", description="Clear bot messages", guild=GUILD_ID)
async def clearbot(interaction: discord.Interaction):
    if not await is_valid_thread(interaction):
        return

    channel = interaction.channel

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
        except Forbidden:
            await interaction.followup.send("❌ I do not have permission to manage messages in this channel.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Could not find the channel.", ephemeral=True)

@bot.tree.command(name="reviewmovie", description="Usage: /reviewmovie <rating> <movie_name> [year_of_release_movie]", guild=GUILD_ID)
async def reviewmovie(interaction: discord.Interaction, rating: int, movie_name: str, year: int = None):
    if not await is_valid_thread(interaction):
        return 
    
    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]

    if not (0 <= rating <= 10):
        await interaction.response.send_message("❌ Please sumbmit a rating ranging from 0 to 10!", ephemeral=True)

    params = {
        'query': movie_name,  # Use 'query' for TMDb API to search by title
        'year': year,
        "api_key": TMDB,  # TMDB API Key, not OMDB
    }

    response = requests.get(f"{BASE_URL}/search/movie", params=params)
    data = response.json()
    movie_data = data['results'][0]

    if(not(db.collection("movies").document(str(movie_data['title'])).get().exists)):
        movie_ref = db.collection("movies").document(str(movie_data['title'])).set({'backdrop_path': movie_data['backdrop_path'], 'release_date': movie_data['release_date'], 'title': movie_data['title']})

    user_ref = db.collection("user").document(str(interaction.user.id))
    rating_ref = user_ref.collection("reviews").document(movie_data['title'])
    rating_doc = rating_ref.get()
    rating_ref.set({'rating': rating})

    await interaction.response.send_message(f"💥 {str(interaction.user.name)} has rated {movie_data['title']} - {str(rating)} 💥", ephemeral=True)

@bot.tree.command(name="reviewdelete", description="Usage: /reviewdelete <movie_name>", guild=GUILD_ID)
async def reviewdel(interaction: discord.Interaction, movie_name:str, year: int = None):

    if not await is_valid_thread(interaction):
        return
    
    params = {
        'query': movie_name,  # Use 'query' for TMDb API to search by title
        'year': year,
        "api_key": TMDB,  # TMDB API Key, not OMDB
    }

    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]
    response = requests.get(f"{BASE_URL}/search/movie", params=params)
    data = response.json()
    movie_data = data['results'][0]

    print(movie_data)
    user_ref = db.collection("user").document(str(interaction.user.id))
    review_ref = user_ref.collection("reviews").document(movie_data['title'])
    print(review_ref.get().to_dict())

    review_ref.delete()

    await interaction.response.send_message(f"✅ Movie {movie_data['title']}'s review has been deleted!", ephemeral=True)

@bot.tree.command(name="reviewlist", description="Usage: /reviewlist [user]", guild=GUILD_ID)
async def reviewlist(interaction:discord.Interaction, user: str = ""):
    
    review_user = get(interaction.guild.members, name=user) if user else None

    if user and review_user is None:
        await interaction.response.send_message(f"❌ {user} could not be found! Please ensure their name is spelled correctly!", ephemeral=True)
        return

    user_object = review_user if review_user else interaction.user

    user_ref = db.collection("user").document(str(user_object.id))
    review_ref = user_ref.collection("reviews")
    review_doc = review_ref.order_by("rating", direction="DESCENDING").stream()

    embed = discord.Embed(title=f"{str(user_object.name)}'s Movie Reviews")

    review_list = [
        [],
        [],
        []
    ]

    if(review_doc):
        for doc in review_doc:
            rating = doc.to_dict().get('rating')
            if(0 <= rating <= 4):
                review_list[0].append(f"   **{str(doc.id)}** - {str(rating)}\n\n")
            elif(5 <= rating <= 7):
                review_list[1].append(f"   **{str(doc.id)}** -  {str(rating)}\n\n")
            elif(8 <= rating <= 10):
                review_list[2].append(f"   **{str(doc.id)}** -  {str(rating)}\n\n")

    for i in range(len(review_list)-1, -1, -1):
        review_value = "\u200b \n"

        for review in review_list[i]:
            review_value += review

        if(i == 2 and review_list[i]):
            embed.add_field(name=f"💥💥💥", value=review_value, inline=False)
            if(review_list[1] or review_list[0]):
                embed.add_field(name="\u200b", value="\n", inline=False)  # Unicode space character
        elif(i == 1 and review_list[i]):
            embed.add_field(name="⭐⭐", value=review_value, inline=False)
            if(review_list[0]):
                embed.add_field(name="\u200b", value="\n", inline=False)  # Unicode space character
        elif(i == 0 and review_list[i]):
            embed.add_field(name="💩", value=review_value, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="getrolemembers", description="Get members apart of KT Max!", guild=GUILD_ID)
async def get_role_members(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, name=ROLE)
    
    if role is None:
        await interaction.response.send_message(f"❌ No role found with the name '{ROLE}'.", ephemeral=True)
        return

    # Get all members with the role
    members_with_role = [member for member in interaction.guild.members if role in member.roles]

    if not members_with_role:
        await interaction.response.send_message(f"❌ No members found with the role '{ROLE}'.", ephemeral=True)
        return
    
    # Send a list of members with that role
    member_names = [member.name for member in members_with_role]
    members_list = "\n".join(member_names)
    
    embed = discord.Embed(
        title=f"Members with the role '{ROLE}'",
        description=members_list,
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="add_role", description="Add the 'KT Max' role to a user", guild=GUILD_ID)
async def add_role(interaction: discord.Interaction, user: discord.Member):
    # Find the role by name
    role = discord.utils.get(interaction.guild.roles, name=ROLE)
    
    if not role:
        await interaction.response.send_message("❌ The 'KT Max' role does not exist.", ephemeral=True)
        return
    
    # Check if the bot has permission to manage roles
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ I don't have permission to manage roles.", ephemeral=True)
        return
    
    # Add the role to the user
    await user.add_roles(role)
    await interaction.response.send_message(f"✅ Successfully added the 'KT Max' role to {user.name}.", ephemeral=True)

@bot.tree.command(name="remove_role", description="Remove the 'KT Max' role from a user", guild=GUILD_ID)
async def remove_role(interaction: discord.Interaction, user: discord.Member):
    # Find the role by name
    role = discord.utils.get(interaction.guild.roles, name=ROLE)
    
    if not role:
        await interaction.response.send_message("❌ The 'KT Max' role does not exist.", ephemeral=True)
        return
    
    # Check if the bot has permission to manage roles
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ I don't have permission to manage roles.", ephemeral=True)
        return
    
    # Remove the role from the user
    await user.remove_roles(role)
    await interaction.response.send_message(f"✅ Successfully removed the 'Kt mAX' role from {user.name}.", ephemeral=True)

@bot.tree.command(name="help", description="Get help with commands!", guild=GUILD_ID)
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="KTCinemaBot Command Help", description=f"Commands parameters: \n\t\t **<>** - Mandatory \n\t\t **[]** Optional")
    embed.add_field(name="/movie <movie_name> [year_of_movie_release]", value="Usage: Add a movie to the discord watchlist\n\t\t <movie_name> - Name of the movie \n\t\t [year_of_movie_release] - Year the movie was released in", inline=False)
    embed.add_field(name="/moviedel <movie_name>", value="Usage: Remove a movie from the discord watchlist \n\t\t <movie_name> Name of the movie", inline=False)
    embed.add_field(name="/movielist", value="Usage: Display discord watchlist", inline=False)
    embed.add_field(name="/moviepoll", value="Usage: Starts a poll for attendance. Input Integer value to select movie", inline=False)
    embed.add_field(name="/clearbot", value="Usage: Clear messages from bot", inline=False)
    embed.add_field(name="/reviewmovie <rating> <movie_name> [year_of_release_movie]", value="Usage: Review a movie \n\t\t <rating> - Integer 0 to 10 \n\t\t <movie_name> - Name of the movie \n\t\t [year_of_movie_release] - Year the movie was released in", inline=False)
    embed.add_field(name="/reviewdel <movie_name>", value="Usage: Delete review \n\t\t <movie_name> - Name of the movie", inline=False)
    embed.add_field(name="/reviewlist [user]", value="Usage: Display list of reviews by user \n\t\t [user] - Name of user", inline=False)
    
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)