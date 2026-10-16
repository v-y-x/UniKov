from discord.ext import commands
import discord
import time

import state

# moderation.py cog is used for basic moderation purposes
# due to discord forbidding prefix commands for large discord bots, this has been implemented for easier and quicker use 

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        state.add_warning(member.id, ctx.author.id, reason)
        warning_count = len(state.get_warnings(member.id))

        await ctx.send(f"⚠️ {member.mention} has been warned for **{reason}**.\nTotal warnings: **{warning_count}**")
        state.add_modstat(ctx.author.id, "warns")

        try:
            await member.send(f"⚠️ You have been warned in *{ctx.guild.name}* for **{reason}**. You currently have **{warning_count}** warning(s).")
        except discord.Forbidden:
            pass

        if warning_count >= 6:
            try:
                await member.ban(reason="🔨 Reached 6 warns, indefinite ban.")
                await ctx.send(f"🔨 {member.mention} has been banned, reached 6 warns")
                state.add_modstat(ctx.author.id, "bans")
            except discord.Forbidden:
                await ctx.send(f"⚠️ {member.mention} reached 6 warns, but I was unable to ban them. Please do it yourself or check my permissions!")

    @commands.command(hidden=True)
    @commands.has_permissions(moderate_members=True)
    async def warnings(self, ctx, member: discord.Member):
        warns = state.get_warnings(member.id)
        if not warns:
            await ctx.send("This user has no warnings.")
            return

        embed = discord.Embed(
            title=f"Warnings for {member.display_name}",
            color=discord.Color.orange()
        )

        for w in warns:
            embed.add_field(
                name=f"<t:{w[2]}:f>",
                value=f"**{w[1]}**\n-# Moderator: <@{w[0]}>",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("The user has a role higher than my highest role, I cannot kick them!")
            return

        try:
            await member.send(f"You were kicked from **{ctx.guild.name}** for: {reason}")
            print(f"{member.name} has been kicked for {reason}")
        except:
            pass

        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 {member.mention} has been kicked for {reason}")
        except discord.Forbidden:
            await ctx.send(f"Unable to kick. Check my permissions!")

    @commands.command(hidden=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("The user has a role higher than my highest role, I cannot ban them!")
            return

        try:
            await member.send(f"You were banned from **{ctx.guild.name}** for: {reason}")
            print(f"{member.name} has been banned for {reason}")
        except:
            pass

        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 {member.mention} has been banned for: {reason}")
            state.add_modstat(ctx.author.id, "bans")
        except discord.Forbidden:
            await ctx.send(f"Unable to ban. Check my permissions!")

    @commands.command(hidden=True)
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member: discord.Object, *, reason: str = "No reason provided"):
        try:
            await ctx.guild.unban(member, reason=reason)
            await ctx.send(f"<@{member.id}> has been unbanned")
        except discord.Forbidden:
            await ctx.send(f"Unable to unban. Check my permissions!")

    MUTED_ROLE_ID = 1555917216631750717

    @commands.command(hidden=True)
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        if member.top_role > ctx.guild.me.top_role:
            await ctx.send("The user has a role higher than my highest role, I cannot mute them!")
            return

        seconds = state.parse_duration(duration)
        if seconds is None:
            await ctx.send("invalid duration! write something like `30m`, `3h` or `1d`.")
            return

        role = ctx.guild.get_role(self.MUTED_ROLE_ID)
        if role is None:
            await ctx.send("Couldn't find the muted role, check that ID is set properly.")
            return
        
        try:
            await member.add_roles(role, reason=reason)
        except discord.Forbidden:
            await ctx.send("Unable to add mute, check my role permissions!")
            return

        expires_at = int(time.time()) + seconds
        state.add_mute_role(member.id, self.MUTED_ROLE_ID, expires_at)

        await ctx.send(f"🔇 {member.mention} has been muted for {duration}. Reason: {reason}")
        print(f"{member.name} has been muted for {duration} | {reason} | UTC: {expires_at}")
        state.add_modstat(ctx.author.id, "mutes")

        try:
            await member.send(f"🔇 You have been muted in **{ctx.guild.name}** for {duration}. Reason: {reason}")
        except:
            pass

    @commands.command(hidden=True)
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        role = ctx.guild.get_role(self.MUTED_ROLE_ID)

        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            await ctx.send("Unable to unmute, check my role permissions!")
            return

        state.remove_temp_role(member.id, self.MUTED_ROLE_ID)  # clean up the pending expiry entry
        await ctx.send(f"🔊 {member.mention} has been unmuted.")
        print(f"{member.name} has been unmuted")

    @commands.command(aliases=["ms"], hidden=True)
    @commands.has_permissions(moderate_members=True)
    async def modstats(self, ctx, member: discord.Member = None): #type: ignore
        if not member:  
            member = ctx.author
        user_id = member.id
        stats = state.get_modstat(user_id)
        if not stats:
            await ctx.send("This user has no stats.")
        else:
            embed = discord.Embed(
                color=discord.Color.og_blurple()
            )
            embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)

            for s in stats: 
                embed.add_field(
                    name="Warns",
                    value=s[0],
                    inline=True
                )
                embed.add_field(
                    name="Warns",
                    value=s[1],
                    inline=True
                )
                embed.add_field(
                    name="Bans",
                    value=s[2],
                    inline=True
                )

            await ctx.send(embed=embed)
        

async def setup(bot): # required for discord.py to reach the cog when running reload commands
    await bot.add_cog(Moderation(bot))