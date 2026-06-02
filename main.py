import asyncio
import os
from typing import Dict, List, Set

import discord
from discord import app_commands
from discord.ext import tasks, commands
from dotenv import load_dotenv
import requests

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
INTRA_UID: str = os.getenv("INTRA_UID", "")
INTRA_SECRET: str = os.getenv("INTRA_SECRET", "")
CAMPUS_ID: int = int(os.getenv("CAMPUS_ID", "9"))
LOG_CHANNEL_ID: int = int(os.getenv("LOG_CHANNEL_ID", "1501554049688932452"))

WHITELIST: Set[str] = {
    "opernod", "lgoderne", "zqian", "cobussie", "crappo", "drafin"
}
BLACKLIST: Set[str] = set()


class IntraBot(commands.Bot):

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.intra_token: str = ""
        self.last_logins: Dict[str, str] = {}
        self.user_whitelists: Dict[int, Set[str]] = {}

    def update_intra_token(self) -> None:
        """Récupère un nouveau token d'accès temporaire via l'Intra."""
        url = "https://api.intra.42.fr/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": INTRA_UID,
            "client_secret": INTRA_SECRET,
        }
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        self.intra_token = resp.json()["access_token"]

    def get_active_logins(self) -> Dict[str, str]:
        """Récupère et filtre les logins actifs du campus."""
        active_allocations: Dict[str, str] = {}
        page = 1

        while True:
            url = f"https://api.intra.42.fr/v2/campus/{CAMPUS_ID}/locations"
            params = {
                "filter[active]": "true",
                "page[size]": 100,
                "page[number]": page
            }
            headers = {"Authorization": f"Bearer {self.intra_token}"}

            try:
                resp = requests.get(
                    url, headers=headers, params=params, timeout=20
                )
                if resp.status_code == 401:
                    self.update_intra_token()
                    headers["Authorization"] = f"Bearer {self.intra_token}"
                    resp = requests.get(
                        url, headers=headers, params=params, timeout=20
                    )

                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                for item in data:
                    user_data = item.get("user")
                    if user_data and "login" in user_data:
                        login = user_data["login"]
                        host = item.get("host", "Inconnu")

                        if login in BLACKLIST:
                            continue

                        active_allocations[login] = host

                page += 1
            except Exception as e:
                print(f"Erreur page {page}: {e}")
                if not active_allocations:
                    return self.last_logins
                return active_allocations

        return active_allocations

    async def setup_hook(self) -> None:
        """Lance la boucle de vérification au démarrage."""
        await self.tree.sync()
        self.check_logs.start()

    async def on_ready(self) -> None:
        print(f"🤖 Bot connecté avec succès en tant que {self.user} !")

    @tasks.loop(minutes=1.0)
    async def check_logs(self) -> None:
        """Compare les états pour envoyer des notifications Discord."""
        current_logins = await asyncio.to_thread(self.get_active_logins)

        if not self.last_logins:
            self.last_logins = current_logins
            return

        current_keys: Set[str] = set(current_logins.keys())
        last_keys: Set[str] = set(self.last_logins.keys())

        arrived = current_keys - last_keys
        left = last_keys - current_keys

        if WHITELIST:
            arrived = arrived.intersection(WHITELIST)
            left = left.intersection(WHITELIST)

        channel = self.get_channel(LOG_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            for login in arrived:
                host = current_logins[login]
                await channel.send(
                    f"📥 **{login}** s'est connecté sur **{host}** !"
                )

            for login in left:
                host = self.last_logins[login]
                await channel.send(f"📤 **{login}** a quitté **{host}**.")

        self.last_logins = current_logins

    @check_logs.before_loop
    async def before_check(self) -> None:
        """Attend que le bot soit prêt avant de lancer la boucle."""
        await self.wait_until_ready()


bot = IntraBot()


@bot.tree.command(name="where", description="Où sont la whitelist")
async def where(interaction: discord.Interaction) -> None:
    if not bot.last_logins:
        await interaction.response.send_message(
            "⏳ Rassemblement des données...", ephemeral=True
        )
        return

    current_wl = bot.user_whitelists.get(interaction.user.id, WHITELIST)
    target_users = sorted(current_wl)

    response: List[str] = []
    for user in target_users:
        host = bot.last_logins.get(user.lower())
        if host:
            response.append(f"✅ **{user}** : {host}")
        else:
            response.append(f"🪐 **{user}** : Knowhere")

    if response:
        await interaction.response.send_message(
            "\n".join(response), ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Ta whitelist est vide.", ephemeral=True
        )


@bot.tree.command(name="whereis", description="Cherche un login")
@app_commands.describe(login="Le login à chercher")
async def whereis(interaction: discord.Interaction, login: str) -> None:
    if not bot.last_logins:
        await interaction.response.send_message(
            "⏳ Rassemblement des données...", ephemeral=True
        )
        return

    user = login.strip()
    host = bot.last_logins.get(user.lower())

    if host:
        await interaction.response.send_message(
            f"✅ **{user}** : {host}", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"🪐 **{user}** : Knowhere", ephemeral=True
        )


@bot.tree.command(name="whitelist", description="Personnalise ta whitelist")
@app_commands.describe(logins="Exemple: opernod, lgoderne")
async def whitelist(interaction: discord.Interaction, logins: str) -> None:
    cleaned = logins.replace(',', ' ').split()
    parsed_logins = {l.strip().lower() for l in cleaned if l.strip()}
    bot.user_whitelists[interaction.user.id] = parsed_logins
    if parsed_logins:
        display = ', '.join(sorted(parsed_logins))
        await interaction.response.send_message(
            f"✅ Whitelist mise à jour : {display}", ephemeral=True
        )
    else:
        bot.user_whitelists.pop(interaction.user.id, None)
        await interaction.response.send_message(
            "✅ Whitelist réinitialisée par défaut.", ephemeral=True
        )


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
