import asyncio
import json
import os
from typing import Dict, List, Optional, Set

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
WHITELISTS_FILE: str = "user_whitelists.json"

WHITELIST: Set[str] = {
    "opernod", "lgoderne", "zqian", "cobussie", "crappo", "drafin", "aluslu"
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
        self.last_api_error: Optional[str] = None
        # Format : {user_id: {"nom_whitelist": {"login1", "login2"}}}
        self.user_whitelists: Dict[int, Dict[str, Set[str]]] = {}
        self.load_whitelists()

    def load_whitelists(self) -> None:
        """Charge les whitelists sauvegardées depuis le fichier JSON."""
        if not os.path.exists(WHITELISTS_FILE):
            return
        try:
            with open(WHITELISTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for uid_str, val in data.items():
                user_id = int(uid_str)
                if isinstance(val, dict):
                    self.user_whitelists[user_id] = {
                        name.lower(): {u.strip().lower() for u in logins if u.strip()}
                        for name, logins in val.items()
                    }
                elif isinstance(val, list):
                    self.user_whitelists[user_id] = {
                        "default": {u.strip().lower() for u in val if u.strip()}
                    }
        except Exception as e:
            print(f"Erreur chargement whitelists: {e}")

    def save_whitelists(self) -> None:
        """Sauvegarde les whitelists de manière atomique dans le fichier JSON."""
        try:
            data = {
                str(uid): {
                    name: sorted(list(logins))
                    for name, logins in user_dict.items()
                }
                for uid, user_dict in self.user_whitelists.items()
            }
            temp_file = f"{WHITELISTS_FILE}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, WHITELISTS_FILE)
        except Exception as e:
            print(f"Erreur sauvegarde whitelists: {e}")

    def get_user_whitelist_names(self, user_id: int) -> List[str]:
        """Retourne les noms de toutes les whitelists d'un utilisateur ('default' toujours inclus)."""
        user_dict = self.user_whitelists.get(user_id, {})
        names = set(user_dict.keys())
        names.add("default")
        sorted_custom = sorted(n for n in names if n != "default")
        return ["default"] + sorted_custom

    def get_user_whitelist(self, user_id: int, nom: str) -> Optional[Set[str]]:
        """Récupère une whitelist spécifique. Si 'default' n'est pas customisé, renvoie la WHITELIST globale."""
        clean_nom = nom.strip().lower()
        user_dict = self.user_whitelists.get(user_id, {})
        if clean_nom in user_dict:
            return user_dict[clean_nom]
        if clean_nom == "default":
            return set(WHITELIST)
        return None

    def set_user_whitelist(self, user_id: int, nom: str, logins: Set[str]) -> None:
        """Définit ou met à jour une whitelist spécifique pour un utilisateur."""
        clean_nom = nom.strip().lower()
        if user_id not in self.user_whitelists:
            self.user_whitelists[user_id] = {}
        self.user_whitelists[user_id][clean_nom] = logins
        self.save_whitelists()

    def delete_user_whitelist(self, user_id: int, nom: str) -> bool:
        """Supprime une whitelist pour un utilisateur. Renvoie True si elle existait."""
        clean_nom = nom.strip().lower()
        if user_id in self.user_whitelists and clean_nom in self.user_whitelists[user_id]:
            del self.user_whitelists[user_id][clean_nom]
            if not self.user_whitelists[user_id]:
                del self.user_whitelists[user_id]
            self.save_whitelists()
            return True
        return False

    def update_intra_token(self) -> None:
        """Récupère un nouveau token d'accès temporaire via l'Intra."""
        url = "https://api.intra.42.fr/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": INTRA_UID,
            "client_secret": INTRA_SECRET,
        }
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 401:
            err_msg = "Clés INTRA_UID / INTRA_SECRET invalides ou expirées dans le .env (401 Unauthorized)."
            self.last_api_error = err_msg
            raise ValueError(err_msg)
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
                self.last_api_error = str(e)
                if not active_allocations:
                    return self.last_logins
                return active_allocations

        self.last_api_error = None
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


async def send_chunked_ephemeral(interaction: discord.Interaction, text: str) -> None:
    """Envoie un message éphémère en le découpant si nécessaire pour respecter la limite de 2000 caractères."""
    chunks: List[str] = []
    current_chunk = ""
    for line in text.split("\n"):
        if len(current_chunk) + len(line) + 1 > 1900:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk = f"{current_chunk}\n{line}" if current_chunk else line
    if current_chunk:
        chunks.append(current_chunk)

    if not chunks:
        await interaction.response.send_message("Aucune donnée.", ephemeral=True)
        return

    if not interaction.response.is_done():
        await interaction.response.send_message(chunks[0], ephemeral=True)
        for c in chunks[1:]:
            await interaction.followup.send(c, ephemeral=True)
    else:
        for c in chunks:
            await interaction.followup.send(c, ephemeral=True)


async def whitelist_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    known = bot.get_user_whitelist_names(interaction.user.id)
    filtered = [name for name in known if current.lower() in name.lower()]
    return [
        app_commands.Choice(name=name, value=name)
        for name in filtered[:25]
    ]


@bot.tree.command(name="where", description="Où sont les étudiants d'une whitelist")
@app_commands.describe(nom="Nom de la whitelist à vérifier (par défaut : default)")
@app_commands.autocomplete(nom=whitelist_autocomplete)
async def where(interaction: discord.Interaction, nom: Optional[str] = "default") -> None:
    if not bot.last_logins:
        if bot.last_api_error:
            await interaction.response.send_message(
                f"⚠️ **Erreur API Intra 42** : Impossible de récupérer les données du campus.\n"
                f"Détail : `{bot.last_api_error}`\n\n"
                f"💡 Vérifie les clés `INTRA_UID` et `INTRA_SECRET` dans le fichier `.env` "
                f"(génère ou vérifie une application sur https://profile.intra.42.fr/oauth/applications).",
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            "⏳ Rassemblement initial des données en cours, réessaie dans quelques secondes...",
            ephemeral=True
        )
        return

    clean_nom = (nom or "default").strip().lower()
    target_wl = bot.get_user_whitelist(interaction.user.id, clean_nom)

    if target_wl is None:
        known = bot.get_user_whitelist_names(interaction.user.id)
        known_display = ", ".join(f"`{k}`" for k in known)
        await interaction.response.send_message(
            f"❌ La whitelist **{clean_nom}** n'existe pas.\n"
            f"📋 Tes whitelists disponibles : {known_display}",
            ephemeral=True
        )
        return

    if not target_wl:
        await interaction.response.send_message(
            f"Ta whitelist **{clean_nom}** est vide.", ephemeral=True
        )
        return

    target_users = sorted(target_wl)
    response: List[str] = [f"📍 **Whitelist : {clean_nom}** ({len(target_users)} membre{'s' if len(target_users) > 1 else ''})"]
    for user in target_users:
        host = bot.last_logins.get(user.lower())
        if host:
            response.append(f"✅ **{user}** : {host}")
        else:
            response.append(f"🪐 **{user}** : Knowhere")

    await send_chunked_ephemeral(interaction, "\n".join(response))


@bot.tree.command(name="whereis", description="Cherche un login")
@app_commands.describe(login="Le login à chercher")
async def whereis(interaction: discord.Interaction, login: str) -> None:
    if not bot.last_logins:
        if bot.last_api_error:
            await interaction.response.send_message(
                f"⚠️ **Erreur API Intra 42** : Impossible de récupérer les données du campus.\n"
                f"Détail : `{bot.last_api_error}`\n\n"
                f"💡 Vérifie les clés `INTRA_UID` et `INTRA_SECRET` dans le fichier `.env`.",
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            "⏳ Rassemblement initial des données en cours, réessaie dans quelques secondes...",
            ephemeral=True
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


@bot.tree.command(name="whitelist", description="Affiche, crée ou modifie une whitelist")
@app_commands.describe(
    nom="Nom de la whitelist (ex: transcendance, par défaut: default)",
    logins="Logins séparés par virgule/espace (ex: opernod, lgoderne). Laisse vide pour afficher.",
)
@app_commands.autocomplete(nom=whitelist_autocomplete)
async def whitelist(
    interaction: discord.Interaction,
    nom: Optional[str] = "default",
    logins: Optional[str] = None,
) -> None:
    raw_nom = (nom or "default").strip()

    # Si l'utilisateur a mis la liste de logins directement dans le premier argument 'nom'
    if logins is None and ("," in raw_nom or " " in raw_nom):
        logins = raw_nom
        clean_nom = "default"
    else:
        clean_nom = raw_nom.lower()

    # Cas 1 : Consultation de la whitelist (aucun login spécifié)
    if logins is None:
        wl = bot.get_user_whitelist(interaction.user.id, clean_nom)
        known = bot.get_user_whitelist_names(interaction.user.id)
        known_display = ", ".join(f"`{k}`" for k in known)

        if wl is None:
            await interaction.response.send_message(
                f"❌ La whitelist **{clean_nom}** n'existe pas.\n"
                f"📋 Tes whitelists disponibles : {known_display}\n"
                f"💡 Pour la créer : `/whitelist nom:{clean_nom} logins:login1, login2`",
                ephemeral=True
            )
            return

        display_members = ", ".join(sorted(wl)) if wl else "*(vide)*"
        msg = (
            f"📋 **Whitelist `{clean_nom}`** ({len(wl)} membre{'s' if len(wl) > 1 else ''}) :\n"
            f"{display_members}\n\n"
            f"📁 **Tes whitelists** : {known_display}\n"
            f"💡 *Pour modifier :* `/whitelist nom:{clean_nom} logins:login1, login2`\n"
            f"🗑️ *Pour supprimer :* `/whitelist nom:{clean_nom} logins:reset`"
        )
        await send_chunked_ephemeral(interaction, msg)
        return

    # Cas 2 : Réinitialisation / suppression demandée
    trimmed_logins = logins.strip().lower()
    if trimmed_logins in {"reset", "clear", "delete", "supprimer", "suppr", "vide", "empty"}:
        if clean_nom == "default":
            bot.delete_user_whitelist(interaction.user.id, "default")
            await interaction.response.send_message(
                "✅ Whitelist **default** réinitialisée avec la liste par défaut du campus.",
                ephemeral=True
            )
        else:
            deleted = bot.delete_user_whitelist(interaction.user.id, clean_nom)
            if deleted:
                await interaction.response.send_message(
                    f"🗑️ Whitelist **{clean_nom}** supprimée.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ La whitelist **{clean_nom}** n'existait pas.", ephemeral=True
                )
        return

    # Cas 3 : Définition / mise à jour des logins
    cleaned = logins.replace(",", " ").split()
    parsed_logins = {l.strip().lower() for l in cleaned if l.strip()}

    if not parsed_logins:
        if clean_nom == "default":
            bot.delete_user_whitelist(interaction.user.id, "default")
            await interaction.response.send_message(
                "✅ Whitelist **default** réinitialisée par défaut.", ephemeral=True
            )
        else:
            bot.delete_user_whitelist(interaction.user.id, clean_nom)
            await interaction.response.send_message(
                f"🗑️ Whitelist **{clean_nom}** supprimée car aucun login valide n'a été fourni.",
                ephemeral=True
            )
        return

    bot.set_user_whitelist(interaction.user.id, clean_nom, parsed_logins)
    display = ", ".join(sorted(parsed_logins))
    await send_chunked_ephemeral(
        interaction,
        f"✅ Whitelist **{clean_nom}** mise à jour ({len(parsed_logins)} membres) :\n{display}"
    )


@bot.tree.command(name="help", description="Guide d'utilisation et aide pour les commandes")
async def help_command(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="🤖 42Bot — Guide d'utilisation",
        description="Ce bot surveille en temps réel les connexions du campus 42 et permet de localiser facilement vos pairs.",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="📍 /where [nom]",
        value=(
            "Affiche l'emplacement actuel des étudiants d'une whitelist.\n"
            "• `/where` : affiche votre whitelist **default**.\n"
            "• `/where nom: transcendance` : affiche la whitelist spécifique **transcendance**.\n"
            "• *Si la liste demandée n'existe pas, le bot vous liste toutes celles disponibles.*\n"
            "• **✅** = Connecté sur un poste (ex: `e1r3p5`)\n"
            "• **🪐** = Knowhere (hors campus / non connecté)"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔍 /whereis <login>",
        value="Recherche le poste de travail actuel d'un login spécifique (ex: `/whereis opernod`).",
        inline=False,
    )
    embed.add_field(
        name="📋 /whitelist [nom] [logins]",
        value=(
            "Gère vos whitelists personnelles (chaque utilisateur Discord a ses propres listes) :\n"
            "• `/whitelist` : consulte votre whitelist **default** et liste toutes vos listes.\n"
            "• `/whitelist nom: transcendance` : consulte le contenu d'une liste spécifique.\n"
            "• `/whitelist logins: opernod, lgoderne` : met à jour votre whitelist **default**.\n"
            "• `/whitelist nom: transcendance logins: login1, login2` : crée ou modifie la liste **transcendance**.\n"
            "• `/whitelist nom: transcendance logins: reset` : supprime la liste **transcendance**.\n"
            "• `/whitelist nom: default logins: reset` : réinitialise votre liste **default** aux étudiants par défaut."
        ),
        inline=False,
    )
    embed.add_field(
        name="💡 Informations & Astuces",
        value=(
            "• **Confidentialité** : Toutes les commandes répondent de façon **éphémère** (vous seul voyez la réponse).\n"
            "• **Autocomplétion** : Discord vous suggère directement le nom de vos whitelists existantes quand vous tapez `nom:`.\n"
            "• **Actualisation** : Les données du campus sont rafraîchies automatiquement toutes les 60 secondes.\n"
            "• **Notifications automatiques** : Le bot annonce les arrivées 📥 et départs 📤 dans le salon dédié."
        ),
        inline=False,
    )
    embed.set_footer(text="42Bot • Fait avec ❤️ pour la communauté 42")
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
