import asyncio
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

from scrapers.simple_scraper import SimpleScraper
from scrapers.kktix_scraper import KKTIXScraper


class DeleteSelect(discord.ui.Select):
    def __init__(self, targets: list[dict], cog: "MonitorCog"):
        self.cog = cog
        options = [
            discord.SelectOption(label=t["name"], value=t["name"])
            for t in targets
        ]
        super().__init__(placeholder="選擇要刪除的票券...", options=options)

    async def callback(self, interaction: discord.Interaction):
        name = self.values[0]
        current_targets = self.cog._load_targets()
        new_targets = [t for t in current_targets if t["name"] != name]
        if len(new_targets) == len(current_targets):
            await interaction.response.send_message(f"找不到：{name}", ephemeral=True)
            return
        self.cog.targets = new_targets
        self.cog.save_config()
        self.cog.targets = self.cog._load_targets()
        await interaction.response.edit_message(content=f"已刪除：{name}", view=None)


class DeleteView(discord.ui.View):
    def __init__(self, targets: list[dict], cog: "MonitorCog"):
        super().__init__(timeout=30)
        self.add_item(DeleteSelect(targets, cog))


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

    def save_config(self):
        config_path = Path("config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config["targets"] = self.targets
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    @tasks.loop(seconds=60)
    async def monitor_check(self):
        targets = self._load_targets()
        for target in targets:
            scraper_type = target.get("type", "simple")

            if scraper_type == "kktix":
                scraper = KKTIXScraper(url=target["url"])
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
                    display_url = target['url'].replace("/register_info", "")
                    await channel.send(
                        f"ticket EXIST!\n{target['name']}: {display_url}"
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
                value=f"URL: {target['url'].replace('/register_info', '')}\nKeyword: {target.get('keyword', '')}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="add_ticket", description="add ticket")
    async def add_ticket(self, interaction: discord.Interaction, name: str, url: str):
        url = url.rstrip("/")
        if "register_info" not in url:
            url = url + "/register_info"

        current_targets = self._load_targets()
        for t in current_targets:
            if t["url"] == url:
                await interaction.response.send_message(f"已存在相同 URL：{url.replace('/register_info', '')}", ephemeral=True)
                return
            if t["name"] == name:
                await interaction.response.send_message(f"已存在相同名稱：{name}", ephemeral=True)
                return

        target = {
            "name": name,
            "type": "kktix",
            "url": url,
            "channel_id": interaction.channel_id
        }
        self.targets = current_targets
        self.targets.append(target)
        self.save_config()
        self.targets = self._load_targets()
        await interaction.response.send_message(f"already add {name}")

    @app_commands.command(name="remove_ticket", description="remove ticket")
    async def remove_ticket(self, interaction: discord.Interaction):
        current_targets = self._load_targets()
        if not current_targets:
            await interaction.response.send_message("目前沒有監控中的票券。", ephemeral=True)
            return
        view = DeleteView(current_targets, self)
        await interaction.response.send_message("請選擇要刪除的票券：", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MonitorCog(bot))