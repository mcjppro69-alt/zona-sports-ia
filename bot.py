import os, json, logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0") or "0")
POST_HOUR = int(os.getenv("POST_HOUR", "9") or "9")
TIMEZONE_NAME = os.getenv("TIMEZONE", "Africa/Luanda")
MAX_DAILY_GAMES = max(1, min(10, int(os.getenv("MAX_DAILY_GAMES", "10") or "10")))
STATE_FILE = os.getenv("STATE_FILE", "state.json")
LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("zona-sports-ai")

SPORTS = {
    "NBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "Premier League": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "La Liga": "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
    "Bundesliga": "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
    "Serie A": "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
    "Ligue 1": "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
    "Champions League": "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
}

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"last_post_date": "", "posted_event_ids": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

async def fetch_json(session, url):
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
        response.raise_for_status()
        return await response.json()

def event_details(event, league_name):
    competitors = event.get("competitions", [{}])[0].get("competitors", []) if event.get("competitions") else []
    home = away = "Equipa por confirmar"
    for c in competitors:
        team = c.get("team", {}).get("displayName", "Equipa")
        if c.get("homeAway") == "home": home = team
        elif c.get("homeAway") == "away": away = team
    status = event.get("status", {}).get("type", {}).get("detail", "Estado indisponível")
    start = event.get("date") or ""
    event_id = str(event.get("id", f"{league_name}-{start}-{home}-{away}"))
    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        when = dt.strftime("%d/%m %H:%M (Luanda)")
    except Exception:
        when = "Hora indisponível"
    return {"id": event_id, "league": league_name, "home": home, "away": away,
            "status": status, "when": when, "date": start}

async def get_events(days=3):
    now, end = datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(days=days)
    results, errors = [], []
    async with aiohttp.ClientSession(headers={"User-Agent": "ZonaSportsAI/1.0"}) as session:
        for league, url in SPORTS.items():
            try:
                data = await fetch_json(session, url)
                for event in data.get("events", []):
                    item = event_details(event, league)
                    try: dt = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                    except Exception: continue
                    if now - timedelta(hours=5) <= dt <= end: results.append(item)
            except Exception as exc:
                log.warning("Falha ao consultar %s: %s", league, exc)
                errors.append(league)
    unique = {e["id"]: e for e in results}
    return sorted(unique.values(), key=lambda x: x["date"]), errors

def format_event(item):
    return f"**{item['league']}** — {item['home']} vs {item['away']}\n🕒 {item['when']} · {item['status']}"

@bot.event
async def on_ready():
    log.info("Ligado como %s (ID: %s)", bot.user, bot.user.id)
    try:
        synced = await bot.tree.sync()
        log.info("Comandos sincronizados: %s", len(synced))
    except Exception:
        log.exception("Não foi possível sincronizar comandos.")
    if not daily_poster.is_running(): daily_poster.start()

@bot.tree.command(name="ajuda", description="Mostra como usar o Zona Sports AI")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="⚽🏀 Zona Sports AI",
        description="Agenda de futebol europeu e NBA com dados públicos.\n\n"
                    "**/jogos** — próximos jogos\n**/jogos liga** — filtra por competição\n"
                    "**/sobre** — fontes e limitações.\n\n"
                    "A agenda pode ter falhas ou atrasos; não garante resultados.",
        color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="jogos", description="Consulta jogos próximos de futebol e NBA")
@app_commands.describe(liga="Opcional: escolhe uma competição")
@app_commands.choices(liga=[app_commands.Choice(name=name, value=name) for name in SPORTS])
async def jogos(interaction: discord.Interaction, liga: app_commands.Choice[str] = None):
    await interaction.response.defer(thinking=True)
    events, errors = await get_events(days=5)
    if liga: events = [e for e in events if e["league"] == liga.value]
    if not events:
        msg = "Não encontrei jogos na agenda neste momento."
        if errors: msg += "\nAlgumas fontes não responderam: " + ", ".join(errors) + "."
        await interaction.followup.send(msg)
        return
    embed = discord.Embed(title="📅 Próximos jogos",
        description="\n\n".join(format_event(e) for e in events[:20]),
        color=discord.Color.blue())
    embed.set_footer(text="Horários em Luanda. Confirma a agenda perto do jogo.")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="sobre", description="Explica as fontes e limitações")
async def sobre(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Esta versão consulta agendas públicas da ESPN. Não inventa probabilidades nem "
        "estatísticas e não classifica jogos como apostas seguras. Para análises quantitativas "
        "é necessário integrar dados estatísticos fiáveis e um método testável.", ephemeral=True)

@tasks.loop(minutes=1)
async def daily_poster():
    now = datetime.now(LOCAL_TZ)
    if now.hour != POST_HOUR or now.minute != 0: return
    state = load_state()
    today = now.date().isoformat()
    if state.get("last_post_date") == today: return
    if not CHANNEL_ID:
        log.warning("CHANNEL_ID não configurado; publicação diária ignorada.")
        return
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        try: channel = await bot.fetch_channel(CHANNEL_ID)
        except Exception:
            log.exception("Não consegui encontrar o canal configurado.")
            return
    events, _ = await get_events(days=1)
    if not events:
        content = "📅 **Zona Sports AI — agenda diária**\nNão consegui confirmar jogos nas fontes públicas agora. Não vou inventar partidas."
    else:
        content = "📅 **Zona Sports AI — agenda diária**\n\n"
        content += "\n\n".join(format_event(e) for e in events[:MAX_DAILY_GAMES])
        content += "\n\n_Informação de agenda, não é garantia nem previsão de resultado._"
    try:
        await channel.send(content)
        state["last_post_date"] = today
        state["posted_event_ids"] = [e["id"] for e in events[:MAX_DAILY_GAMES]]
        save_state(state)
    except Exception:
        log.exception("Falha ao publicar agenda diária.")

@daily_poster.before_loop
async def before_daily_poster():
    await bot.wait_until_ready()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("Falta DISCORD_TOKEN. Configura-o como variável de ambiente; nunca o publiques.")
    bot.run(DISCORD_TOKEN)
