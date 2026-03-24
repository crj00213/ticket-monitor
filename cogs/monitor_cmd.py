import asyncio
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

from scrapers.simple_scraper import SimpleScraper
from scrapers.kktix_scraper import KktixScraper


class MonitorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.targets = self._load_targets()
        self.monitor_check.start()

    def _load_targets(self) -> list[dict]:
        config_path = Path("config.json")
        if not config_path.exists():
            raise FileNotFoundError("config.json not found")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("targets", [])

    @tasks.loop(seconds=60)
    async def monitor_check(self):
        for target in self.targets:
            scraper_type = target.get("type", "simple")

            if scraper_type == "kktix":
                scraper = KktixScraper(url=target["url"])
            else:
                scraper = SimpleScraper(
                    url=target["url"],
                    keyword=target["keyword"]
                )

            is_available = await scraper.check_status()

            if is_available:
                channel_id = target.get("channel_id")
                if not channel_id:
                    continue

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    print(f"[ERROR] Cannot find channel {channel_id} (target: {target['name']})")
                    continue

                print(f"[OK] Found channel: {channel.name} ({channel_id})")  # type: ignore

                if not isinstance(channel, discord.TextChannel):
                    print(f"[ERROR] Channel {channel_id} is not a text channel")
                    continue

                try:
                    await channel.send(
                        f"ticket EXIST!\n{target['url']}"
                    )
                except discord.Forbidden:
                    print(f"[ERROR] Bot does not have permission to send message in channel {channel.id}")
                except Exception as e:
                    print(f"[ERROR] Other error: {e}")

    @monitor_check.before_loop
    async def before_monitor_check(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(1)

    @app_commands.command(name="status", description="list monitored URLs")
    async def status(self, interaction: discord.Interaction):
        if not self.targets:
            await interaction.response.send_message("Currently no monitored targets.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Currently Monitored URLs",
            color=discord.Color.blue()
        )

        for i, target in enumerate(self.targets, 1):
            embed.add_field(
                name=f"{i}. {target['name']}",
                value=f"URL: {target['url']}\nKeyword: {target['keyword']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MonitorCog(bot))