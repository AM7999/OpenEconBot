import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import sqlite3
import time

import asyncio
import signal
import json

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

db_connections = {}
settings = { 'guild_settings': [] }

with open("items.json", "r") as file:
  data = json.load(file)

with open("config.json", "r") as file:
  config = json.load(file)
  config["guild_settings"].sort(key=lambda x: x["gid"])
  settings = config

def initDB(conn: sqlite3.Connection):
  conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
      user_id INTEGER PRIMARY KEY,
      username TEXT,
      balance REAL,
      inventory TEXT DEFAULT '[]'
    )
    """)
  conn.commit()
    
def getDB(guild_id: int) -> sqlite3.Connection:
  if not os.path.isdir("dbs"):
    os.mkdir("dbs")
  if guild_id not in db_connections:
    db_connections[guild_id] = sqlite3.connect(f"dbs/guild_{guild_id}.db")
    db_connections[guild_id].row_factory = sqlite3.Row
    initDB(db_connections[guild_id])
  return db_connections[guild_id]

def saveAlldbs():
  for guild_id, conn in db_connections.items():
    conn.commit()
    conn.close()
    print(f"Saved for: {guild_id}")
  db_connections.clear()

async def shutdown():
  print("stopping")
  saveAlldbs()
  await bot.close()

# ! Events ==================

@bot.event
async def on_guild_join(guild):
  getDB(guild.id)
  print(f"created db: {guild.name} ({guild.id})")

@bot.event
async def on_ready():
  guilds = bot.guilds
  print(f"Logged in: {bot.user}")
  for guild in guilds:
    print(f"  Guild: {guild.id}")
  for guild in bot.guilds:
    start = time.perf_counter()
    getDB(guild.id)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"DB ready for guild: {guild.name} ({guild.id}). Took: {elapsed:.2f}")


@bot.event
async def on_message(message):
  print(f"Message from {message.author}: {message.content}")
  await bot.process_commands(message)

# error handler
@bot.event
async def on_command_error(ctx, error):
  print(str(error))
  data = {"embeds": [{"title": "Oops, An error occurred!", "description": str(error), "color": 13247010}]}
  embed = discord.Embed.from_dict(data["embeds"][0])
  await ctx.send(embed=embed)

# ! End of events ===========

# ! Commands ================

@bot.command()
async def increaseMoney(ctx, username: str, val: int):
  conn = getDB(ctx.guild.id)
  user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
  print(user)
  if user is None:
    await ctx.send("You aren't Registered! run !register to Register")
    return
  newBalance = user["balance"] + val
  conn.execute("UPDATE users SET balance = ? WHERE username = ?", (newBalance,username,))
  conn.commit()


@bot.command()
async def purchaseItem(ctx, item):
  conn = getDB(ctx.guild.id)
  user = conn.execute("SELECT * FROM users WHERE user_id = ?", (ctx.author.id,)).fetchone()
  if user is None:
    await ctx.send("You aren't Registered! run !register to Register")
    return
  
  itemData = None
  for i in data["items"]:
    if i["id"] == item:
      itemData = i
      break
  
  if itemData is None:
    await ctx.send(f"Item with id: `{item}` does not exist!")
    return
  
  if user["balance"] < itemData["price"]:
    await ctx.send("You don't have enough money to purchase this item!")
    return
  
  newBalance = user["balance"] - itemData["price"]
  user['inventory'] = json.loads(user['inventory'])
  user['inventory'].append(itemData['id'])
  conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (newBalance,ctx.author.id,))
  conn.execute("UPDATE users SET inventory = ? WHERE user_id = ?", (json.dumps(user['inventory']), ctx.author.id,))
  conn.commit()
  await ctx.send(f"You have purchased: {itemData['name']} for ${itemData['price']}! Your new balance is ${newBalance}.")

@bot.command()
async def listItems(ctx):
  embedData = json.loads('''{"content":null,"embeds":[{"title":"Items","color":5814783,"fields":[]}],"attachments":[]}''')
  itemList = ""
  for item in data["items"]:
    item = { 'name': item['name'] + " - " + '`' +item['id'] + '`', 'value': item['desc'] + "\n" + f"${item['price']}" }
    print(str(item))
    embedData["embeds"][0]["fields"].append(item)
    print(str(embedData["embeds"][0]["fields"]))
    
  embed = discord.Embed.from_dict(embedData["embeds"][0])
  await ctx.send(embed=embed)

@bot.command()
async def register(ctx):
  start = time.perf_counter()

  conn = getDB(ctx.guild.id)
  existed = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,)).fetchone()

  if existed:
    await ctx.send("You cant register twice!")
    return
  
  conn.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (ctx.author.id, ctx.author.name, 100.0))
  conn.commit()

  elapsed = (time.perf_counter() - start) * 1000
  print(f"{elapsed:.2f}")

  await ctx.send(f"registered: {ctx.author.id}.")

@bot.command()
async def delete(ctx, userid):
  conn = getDB(ctx.guild.id)
  existed = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (userid,)).fetchone()

  if not existed:
    await ctx.send(f"userid: {userid} does not exist in db")
  
  conn.execute("DELETE FROM users WHERE user_id = ?", (userid,))
  conn.commit()
  await ctx.send(f"user {userid} removed from db")

@bot.command()
async def clearDB(ctx):
  conn = getDB(ctx.guild.id)
  conn.execute("DELETE FROM users")
  conn.commit()
  await ctx.send("Cleared DB. For Better results delete the db itself in the dbs folder")

# ! End of Commands =========

token = os.getenv("BOT_TOKEN")

if token is None:
    print("Please set BOT_TOKEN in .env!")
    exit(1)

bot.run(token)