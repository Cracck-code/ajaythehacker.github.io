import discord
from discord.ext import commands
from discord import app_commands
import datetime
import json
import os
import aiohttp
import asyncio
import uuid
from typing import List

# --- CONFIGURATION ---
TOKEN = "MTQ4MDE5NjgyMTI4MzI0MjA2NA.GeSj-Z.UMjSJ6lnsN3X8rEA-wM6CkPirGAGxcTWK_nNcI" 

CONFIG_FILE = "config.json"
DATA_FILE = "user_data.json"
PENDING_LOGS_FILE = "pending_logs.json"

ITA_BLUE = 0x0047AB
METAR_API_URL = "https://api.checkwx.com/metar/{}/decoded"
METAR_API_KEY = "b4acfe7faf134a318fab795f4886a2d2" 

FLEET_DATA = {
    "Airbus A320-200": {
        "image": "https://cdn.discordapp.com/attachments/1467123193205493900/1471539455348445470/Screenshot_278.png",
        "description": "The A320-200 is the heart of ITA Airways' short and medium-haul operations in Europe."
    },
    "Airbus A350-900": {
        "image": "https://cdn.discordapp.com/attachments/1467123193205493900/1471539454920364115/Screenshot_276.png",
        "description": "The A350-900 is the flagship of the fleet for long-haul intercontinental routes."
    },
    "Boeing 727-200": {
        "image": "https://cdn.discordapp.com/attachments/1467123193205493900/1471539455889375436/Screenshot_279.png",
        "description": "An aviation icon, the Boeing 727 trijet represents the history of flight in our hangar."
    },
    "McDonnell Douglas MD-11": {
        "image": "https://cdn.discordapp.com/attachments/1467123193205493900/1471539456518656080/Screenshot_280.png",
        "description": "The legendary MD-11 trijet, known for its power and unmistakable design."
    }
}

TIERS = {
    "Venezia": {"price": 100000, "emoji": "🛶"},
    "Napoli": {"price": 250000, "emoji": "🌋"},
    "Milano": {"price": 500000, "emoji": "⛪"},
    "Roma": {"price": 1000000, "emoji": "🏛️"}
}

# --- DATA PERSISTENCE ---
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f: return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f: json.dump(data, f, indent=4)

def update_user_stats(user_id, guild_id, flights=0, money=0, last_daily=None, rank=None, callsign=None, is_staff=False):
    data = load_json(DATA_FILE)
    sid, uid = str(guild_id), str(user_id)
    if sid not in data: data[sid] = {}
    if uid not in data[sid]:
        data[sid][uid] = {
            "flights": 0, 
            "balance": 0, 
            "rank": "Cadet", 
            "callsign": "N/A",
            "joined": str(datetime.date.today()), 
            "last_daily": "2000-01-01"
        }
    
    user = data[sid][uid]
    user["flights"] = max(0, user.get("flights", 0) + flights)
    
    if is_staff and money < 0:
        pass 
    else:
        user["balance"] = max(0, user.get("balance", 0) + money)
        
    if last_daily: user["last_daily"] = last_daily
    if rank: user["rank"] = rank
    if callsign: user["callsign"] = callsign
    
    save_json(DATA_FILE, data)
    return user

# --- UI COMPONENTS ---

class ContractView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Contract", style=discord.ButtonStyle.success, emoji="✅", custom_id="claim_contract")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.set_field_at(5, name="**Status**", value=f"🔴 `Claimed by {interaction.user.display_name}`", inline=True)
        button.disabled = True
        button.label = "Claimed"
        button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"✈️ {interaction.user.mention}, contract accepted!", ephemeral=True)

class LogApprovalView(discord.ui.View):
    def __init__(self, pilot_id: str, log_id: str):
        super().__init__(timeout=None)
        self.pilot_id = pilot_id
        self.log_id = log_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅", custom_id="approve_log_btn")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Only staff can approve logs.", ephemeral=True)
        
        reward = 5000
        update_user_stats(int(self.pilot_id), interaction.guild_id, flights=1, money=reward)
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_field_at(4, name="**Status**", value=f"✅ `Approved by {interaction.user.display_name}`", inline=False)
        
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(f"✅ Log approved. Pilot rewarded with $5,000.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="cancel_log_btn")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Only staff can reject logs.", ephemeral=True)
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_field_at(4, name="**Status**", value=f"❌ `Rejected by {interaction.user.display_name}`", inline=False)
        
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(f"❌ Log rejected. No rewards issued.", ephemeral=True)

class AirlineBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=".", intents=intents)

    async def setup_hook(self):
        self.add_view(ContractView())

bot = AirlineBot()

@bot.event
async def on_ready():
    print(f'--- ITA AIRWAYS UTILITIES ONLINE ---')

# --- SYSTEM COMMANDS ---

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_prefix(ctx):
    await ctx.send("⏳ Syncing...")
    synced = await bot.tree.sync()
    await ctx.send(f"✅ {len(synced)} slash commands synced!")

@bot.tree.command(name="setup", description="Initial Configuration (Admin Only)")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, 
                log_channel: discord.TextChannel, 
                contract_channel: discord.TextChannel,
                venezia_role: discord.Role,
                napoli_role: discord.Role,
                milano_role: discord.Role,
                roma_role: discord.Role):
    
    config = load_json(CONFIG_FILE)
    config[str(interaction.guild_id)] = {
        "log_channel": log_channel.id, 
        "contract_channel": contract_channel.id,
        "roles": {
            "Venezia": venezia_role.id,
            "Napoli": napoli_role.id,
            "Milano": milano_role.id,
            "Roma": roma_role.id
        }
    }
    save_json(CONFIG_FILE, config)
    await interaction.response.send_message("✅ Configuration updated successfully!")

# --- ECONOMY & LEADERBOARD ---

@bot.tree.command(name="balance", description="Check your current balance")
async def balance(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    
    data = load_json(DATA_FILE).get(str(interaction.guild_id), {}).get(str(target.id), {})
    current_balance = data.get("balance", 0)
    
    embed = discord.Embed(title="💰 Bank Balance", color=ITA_BLUE)
    embed.description = f"Balance of {target.mention}:\n# `${current_balance:,}`"
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="View the top pilots (Flights or Cash)")
@app_commands.choices(sort_by=[
    app_commands.Choice(name="Cash", value="balance"),
    app_commands.Choice(name="Flights", value="flights")
])
async def leaderboard(interaction: discord.Interaction, sort_by: str = "flights"):
    data = load_json(DATA_FILE).get(str(interaction.guild_id), {})
    lb = []
    for uid, stats in data.items():
        member = interaction.guild.get_member(int(uid))
        if member:
            lb.append({
                "name": member.display_name,
                "value": stats.get(sort_by, 0),
                "other": stats.get("flights" if sort_by == "balance" else "balance", 0)
            })
    
    sorted_lb = sorted(lb, key=lambda x: x["value"], reverse=True)[:10]
    title = "🏦 Rich List" if sort_by == "balance" else "✈️ Top Aviators"
    embed = discord.Embed(title=f"{title} - Global", color=ITA_BLUE)
    
    desc = ""
    for i, entry in enumerate(sorted_lb, 1):
        if sort_by == "balance":
            desc += f"**{i}.** {entry['name']} — `${entry['value']:,}` ({entry['other']} flights)\n"
        else:
            desc += f"**{i}.** {entry['name']} — **{entry['value']}** flights (`${entry['other']:,}`)\n"
            
    embed.description = desc or "No data available."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pay", description="Transfer money to another pilot")
async def pay(interaction: discord.Interaction, receiver: discord.Member, amount: int):
    if amount <= 0 or receiver.id == interaction.user.id: 
        return await interaction.response.send_message("❌ Invalid operation.", ephemeral=True)
    
    is_staff = interaction.user.guild_permissions.administrator
    
    if not is_staff:
        data = load_json(DATA_FILE).get(str(interaction.guild_id), {}).get(str(interaction.user.id), {})
        if data.get("balance", 0) < amount:
            return await interaction.response.send_message("❌ Insufficient funds.", ephemeral=True)
    
    update_user_stats(interaction.user.id, interaction.guild_id, money=-amount, is_staff=is_staff)
    update_user_stats(receiver.id, interaction.guild_id, money=amount)
    
    staff_note = " (Staff Grant)" if is_staff else ""
    await interaction.response.send_message(f"✅ Sent **${amount:,}** to {receiver.mention}{staff_note}")

@bot.tree.command(name="daily", description="Claim your daily salary ($1,000)")
async def daily(interaction: discord.Interaction):
    data = load_json(DATA_FILE).get(str(interaction.guild_id), {}).get(str(interaction.user.id), {})
    today = str(datetime.date.today())
    if data.get("last_daily") == today:
        return await interaction.response.send_message("❌ Salary already claimed today!", ephemeral=True)
    
    update_user_stats(interaction.user.id, interaction.guild_id, money=1000, last_daily=today)
    await interaction.response.send_message("💰 You received your salary of **$1,000**!")

# --- STAFF TOOLS ---

@bot.tree.command(name="addflight", description="Add flights to a pilot (Staff Only)")
@app_commands.checks.has_permissions(administrator=True)
async def addflight(interaction: discord.Interaction, member: discord.Member, amount: int):
    update_user_stats(member.id, interaction.guild_id, flights=amount)
    await interaction.response.send_message(f"✈️ Added **{amount}** flights to {member.display_name}.")

@bot.tree.command(name="addcash", description="Add money to a pilot (Staff Only)")
@app_commands.checks.has_permissions(administrator=True)
async def addcash(interaction: discord.Interaction, member: discord.Member, amount: int):
    update_user_stats(member.id, interaction.guild_id, money=amount)
    await interaction.response.send_message(f"💵 Credited **${amount:,}** to {member.display_name}.")

@bot.tree.command(name="removecash", description="Remove money from a pilot (Staff Only)")
@app_commands.checks.has_permissions(administrator=True)
async def removecash(interaction: discord.Interaction, member: discord.Member, amount: int):
    update_user_stats(member.id, interaction.guild_id, money=-amount)
    await interaction.response.send_message(f"💸 Removed **${amount:,}** from {member.display_name}.")

# --- FEEDBACK & REVIEWS ---

@bot.tree.command(name="review", description="Submit a review for the server and airline")
async def review(interaction: discord.Interaction, rating: int, comment: str):
    if rating < 1 or rating > 5:
        return await interaction.response.send_message("❌ Rating must be between 1 and 5 stars.", ephemeral=True)
    
    stars = "⭐" * rating
    embed = discord.Embed(title="🌟 New Server Review", color=ITA_BLUE)
    embed.add_field(name="User", value=interaction.user.mention, inline=True)
    embed.add_field(name="Rating", value=stars, inline=True)
    embed.add_field(name="Feedback", value=f"```{comment}```", inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text=f"Submitted on {datetime.date.today()}")
    
    await interaction.response.send_message(f"✅ Thank you for your feedback, {interaction.user.display_name}!", ephemeral=True)
    await interaction.channel.send(embed=embed)

# --- FLIGHT OPERATIONS ---

@bot.tree.command(name="setcallsign", description="Set your official pilot callsign")
async def setcallsign(interaction: discord.Interaction, callsign: str):
    update_user_stats(interaction.user.id, interaction.guild_id, callsign=callsign.upper())
    await interaction.response.send_message(f"✅ Your callsign has been set to **{callsign.upper()}**")

@bot.tree.command(name="flightlog", description="Log a completed flight for review")
async def flightlog(interaction: discord.Interaction, callsign: str, departure: str, arrival: str, aircraft: str, screenshot: discord.Attachment, remarks: str = "None"):
    config = load_json(CONFIG_FILE).get(str(interaction.guild_id), {})
    if "log_channel" not in config: return await interaction.response.send_message("❌ Log channel not configured.", ephemeral=True)
    
    log_id = str(uuid.uuid4())[:8].upper()
    channel = bot.get_channel(config["log_channel"])
    
    embed = discord.Embed(title="✈️ PENDING FLIGHT LOG", color=ITA_BLUE)
    embed.add_field(name="**Log ID**", value=f"`{log_id}`", inline=True)
    embed.add_field(name="**Callsign**", value=f"`{callsign.upper()}`", inline=True)
    embed.add_field(name="**Aircraft**", value=f"✈️ `{aircraft.upper()}`", inline=True)
    embed.add_field(name="**Route**", value=f"🌐 `{departure.upper()}` ➔ `{arrival.upper()}`", inline=False)
    embed.add_field(name="**Status**", value="⏳ `Awaiting Approval` (Staff use button below)", inline=False)
    embed.set_image(url=screenshot.url)
    embed.set_footer(text=f"Pilot ID: {interaction.user.id} | Name: {interaction.user.display_name}")
    
    view = LogApprovalView(pilot_id=str(interaction.user.id), log_id=log_id)
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Flight logged! Log ID: `{log_id}`. Staff will review it shortly.", ephemeral=True)

@bot.tree.command(name="flightstats", description="View your flight statistics")
async def flightstats(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    stats = load_json(DATA_FILE).get(str(interaction.guild_id), {}).get(str(target.id), {})
    
    embed = discord.Embed(title="📊 Pilot Record", color=ITA_BLUE)
    embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
    embed.add_field(name="Callsign", value=f"`{stats.get('callsign', 'N/A')}`", inline=True)
    embed.add_field(name="Total Flights", value=f"✈️ `{stats.get('flights', 0)}`", inline=True)
    embed.add_field(name="Rank", value=f"🎖️ `{stats.get('rank', 'Cadet')}`", inline=True)
    embed.add_field(name="Balance", value=f"${stats.get('balance', 0):,}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="postcontract", description="Post a new flight contract (Staff Only)")
@app_commands.checks.has_permissions(administrator=True)
async def postcontract(interaction: discord.Interaction, callsign: str, route: str, aircraft: str, reward: int, description: str):
    config = load_json(CONFIG_FILE).get(str(interaction.guild_id), {})
    if "contract_channel" not in config: return await interaction.response.send_message("❌ Contract channel not configured.", ephemeral=True)
    
    contract_id = f"ITA-{str(uuid.uuid4())[:5].upper()}"
    channel = bot.get_channel(config["contract_channel"])
    
    embed = discord.Embed(title="📜 NEW FLIGHT CONTRACT", color=ITA_BLUE)
    embed.description = f"**Description:**\n{description}"
    embed.add_field(name="**Contract ID**", value=f"`{contract_id}`", inline=True)
    embed.add_field(name="**Callsign**", value=f"`{callsign.upper()}`", inline=True)
    embed.add_field(name="**Aircraft**", value=f"✈️ `{aircraft}`", inline=True)
    embed.add_field(name="**Route**", value=f"🌐 `{route}`", inline=False)
    embed.add_field(name="**Reward**", value=f"💰 `${reward:,}`", inline=True)
    embed.add_field(name="**Status**", value="🟢 `Available`", inline=True)
    
    await channel.send(embed=embed, view=ContractView())
    await interaction.response.send_message(f"✅ Contract `{contract_id}` posted!", ephemeral=True)

@bot.tree.command(name="buy", description="Purchase a city-based rank")
@app_commands.choices(tier=[app_commands.Choice(name=f"{k} (${v['price']:,})", value=k) for k,v in TIERS.items()])
async def buy(interaction: discord.Interaction, tier: str):
    config = load_json(CONFIG_FILE).get(str(interaction.guild_id), {})
    if "roles" not in config: return await interaction.response.send_message("❌ Setup not completed.", ephemeral=True)
    
    is_staff = interaction.user.guild_permissions.administrator
    price = TIERS[tier]["price"]
    
    if not is_staff:
        data = load_json(DATA_FILE).get(str(interaction.guild_id), {}).get(str(interaction.user.id), {})
        if data.get("balance", 0) < price:
            return await interaction.response.send_message(f"❌ Insufficient funds.", ephemeral=True)
    
    update_user_stats(interaction.user.id, interaction.guild_id, money=-price, rank=tier, is_staff=is_staff)
    role_id = config["roles"].get(tier)
    if role_id:
        role = interaction.guild.get_role(role_id)
        if role: await interaction.user.add_roles(role)
    
    await interaction.response.send_message(f"🎊 Congratulations! You are now a **{tier}** level pilot!")

# --- UTILITIES ---

@bot.tree.command(name="metar", description="Get current METAR for an ICAO code")
async def metar(interaction: discord.Interaction, icao: str):
    await interaction.response.defer()
    headers = {"X-API-Key": METAR_API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.get(METAR_API_URL.format(icao.upper()), headers=headers) as r:
            if r.status == 200:
                data = await r.json()
                raw = data["data"][0].get("raw_text", "N/A")
                await interaction.followup.send(f"🌡️ **METAR {icao.upper()}**:\n`{raw}`")
            else:
                await interaction.followup.send("❌ Could not retrieve weather data.")

@bot.tree.command(name="fleet", description="View info about an aircraft")
async def fleet(interaction: discord.Interaction, aircraft: str):
    data = FLEET_DATA.get(aircraft)
    if not data: return await interaction.response.send_message("❌ Aircraft not found in fleet.")
    embed = discord.Embed(title=aircraft, description=data["description"], color=ITA_BLUE)
    embed.set_image(url=data["image"])
    await interaction.response.send_message(embed=embed)

@fleet.autocomplete('aircraft')
async def fleet_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    return [app_commands.Choice(name=name, value=name) for name in FLEET_DATA.keys() if current.lower() in name.lower()]

bot.run(TOKEN)
