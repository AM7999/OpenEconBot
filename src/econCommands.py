from discord.ext import commands

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def purchase(ctx, item):
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
            await ctx.send(f"item with id: '{item}' does not exist!")
            return
        
        if user["balance"] - itemData["price"]