import os
from glob import glob

import discord
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

class MyBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        cogs_path = "cogs"
        for cog_file in glob(f"{cogs_path}/*.py"):
            module_name = cog_file.replace("/", ".").replace("\\", ".").replace(".py", "")
            await self.load_extension(module_name)

    async def on_ready(self):
        print(f"working: {self.user}")


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Please set DISCORD_TOKEN in the .env file.")

    bot = MyBot()
    bot.run(token)


if __name__ == "__main__":
    main()
