import asyncio
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

from scrapers.simple_scraper import SimpleScraper
from scrapers.kktix_scraper import KKTIXScraper


class PriceLabelModal(discord.ui.Modal, title="輸入票種金額"):
    def __init__(self, selected_indices: list[str], id_map: dict[str, int], view: "TicketSelectView"):
        super().__init__()
        self.selected_indices = selected_indices
        self.id_map = id_map
        self.ticket_view = view
        self.inputs: list[discord.ui.TextInput] = []

        for i in selected_indices:
            text_input = discord.ui.TextInput(
                label=f"價位 {i} 的金額",
                placeholder="例如 TWD$6,280",
                max_length=10,
                required=True
            )
            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        view = self.ticket_view
        watched_tickets = [
            {"id": self.id_map[i], "label": self.inputs[n].value}
            for n, i in enumerate(self.selected_indices)
        ]
        target = {
            "name": view.name,
            "type": "kktix",
            "url": view.url,
            "channel_id": view.channel_id,
            "watched_tickets": watched_tickets,
        }
        current_targets = view.cog._load_targets()
        current_targets.append(target)
        view.cog.targets = current_targets
        view.cog.save_config()
        view.cog.targets = view.cog._load_targets()

        labels = "、".join(w["label"] for w in watched_tickets)
        await interaction.response.edit_message(
            content=f"已新增 **{view.name}**，監控：{labels}",
            view=None
        )


class TicketSelect(discord.ui.Select):
    def __init__(self, sorted_tickets: list[dict]):
        self.id_map = {str(i + 1): t["id"] for i, t in enumerate(sorted_tickets)}
        n = len(sorted_tickets)
        options = [
            discord.SelectOption(label=str(i + 1), value=str(i + 1))
            for i in range(n)
        ]
        super().__init__(
            placeholder="請選擇您要監控的票券在網頁上是第幾個？（第一個請點擊１）",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        view: TicketSelectView = self.view  # type: ignore
        selected_indices = sorted(self.values, key=lambda x: int(x))
        modal = PriceLabelModal(selected_indices, self.id_map, view)
        await interaction.response.send_modal(modal)


class TicketSelectView(discord.ui.View):
    def __init__(self, tickets: list[dict], name: str, url: str, channel_id: int, cog: "MonitorCog"):
        super().__init__(timeout=60)
        self.name = name
        self.url = url
        self.channel_id = channel_id
        self.cog = cog

        sorted_tickets = sorted(tickets, key=lambda x: x["id"])
        self.add_item(TicketSelect(sorted_tickets))


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
                watched_tickets = target.get("watched_tickets")
                if watched_tickets:
                    ticket_ids = [t["id"] for t in watched_tickets]
                    available_ids = await scraper.check_specific_tickets(ticket_ids)
                    is_available = bool(available_ids)
                    available_labels = [t["label"] for t in watched_tickets if t["id"] in available_ids]
                else:
                    is_available = await scraper.check_status()
                    available_labels = []
            else:
                scraper = SimpleScraper(
                    url=target["url"],
                    keyword=target["keyword"]
                )
                is_available = await scraper.check_status()
                available_labels = []

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
                    ticket_info = f"\n票種：{', '.join(available_labels)}" if available_labels else ""
                    await channel.send(
                        f"ticket EXIST!\n{target['name']}: {display_url}{ticket_info}"
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

        await interaction.response.defer(ephemeral=True)
        scraper = KKTIXScraper(url=url)
        tickets = await scraper.fetch_tickets()

        if not tickets:
            await interaction.followup.send("無法取得票種資訊，請確認 URL 是否正確。", ephemeral=True)
            return

        content = f"**{name}** 找到 {len(tickets)} 個票券，請對照 KKTIX 頁面選擇要監控的項目："
        view = TicketSelectView(tickets, name, url, interaction.channel_id, self)
        await interaction.followup.send(content, view=view, ephemeral=True)

    @app_commands.command(name="inspect", description="查看活動的 sections 原始資料")
    async def inspect(self, interaction: discord.Interaction, name: str):
        targets = self._load_targets()
        target = next((t for t in targets if t["name"] == name), None)
        if not target:
            await interaction.response.send_message(f"找不到：{name}", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        scraper = KKTIXScraper(url=target["url"])
        sections = await scraper.fetch_sections()

        if not sections:
            await interaction.followup.send("沒有 sections 資料或抓取失敗", ephemeral=True)
            return

        lines = []
        for i, s in enumerate(sections):
            lines.append(f"**Section {i}**")
            for k, v in s.items():
                lines.append(f"  `{k}`: {v}")

        text = "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900] + "\n...(truncated)"

        await interaction.followup.send(text, ephemeral=True)

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