import discord
from discord.ext import commands
from discord import app_commands
from Data.tables import Character, Account, Business
from Data import engine
from sqlalchemy.orm import Session
from sqlalchemy import select

class Cog(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot) -> None:
        super().__init__()
        self.bot = bot

    async def private_account_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete for a user's own Accounts (Characters & Businesses)"""
        with Session(engine) as session:
            # Find Characters owned by the user
            char_stmt = select(Character).where(
                Character.name.ilike(f"%{current}%"),
                Character.discord_id == interaction.user.id
            ).limit(25)
            characters = session.scalars(char_stmt).all()

            # Find Businesses owned by the user
            biz_stmt = select(Business).join(Business.owner).where(
                Business.name.ilike(f"%{current}%"),
                Character.discord_id == interaction.user.id
            ).limit(25)
            businesses = session.scalars(biz_stmt).all()

            choices = []
            for char in characters:
                if char.account:
                    choices.append(app_commands.Choice(name=f"[👤] {char.name}", value=str(char.account.id)))
            
            for biz in businesses:
                if biz.account:
                    choices.append(app_commands.Choice(name=f"[🏢] {biz.name}", value=str(biz.account.id)))

            return choices[:25]

    async def public_account_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete for any Account"""
        with Session(engine) as session:
            char_stmt = select(Character).where(Character.name.ilike(f"%{current}%")).limit(25)
            characters = session.scalars(char_stmt).all()

            biz_stmt = select(Business).where(Business.name.ilike(f"%{current}%")).limit(25)
            businesses = session.scalars(biz_stmt).all()

            choices = []
            for char in characters:
                if char.account:
                    choices.append(app_commands.Choice(name=f"[👤] {char.name}", value=str(char.account.id)))
            
            for biz in businesses:
                if biz.account:
                    choices.append(app_commands.Choice(name=f"[🏢] {biz.name}", value=str(biz.account.id)))

            return choices[:25]

    def _error_embed(self, message: str) -> discord.Embed:
        return discord.Embed(title="Error", description=message, color=discord.Color.red())

    @app_commands.command(name="create", description="Create a new character")
    async def create(self, interaction: discord.Interaction, name: str):
        try:
            with Session(engine) as session:
                existing_char = session.get(Character, name)
                if existing_char:
                    return await interaction.response.send_message(embed=self._error_embed(f"Character `{name}` already exists."))

                new_char = Character(
                    name=name, 
                    discord_id=interaction.user.id, 
                )
                session.add(new_char)
                session.commit()

                embed = discord.Embed(
                    title="Character Created",
                    description=f"Character **{name}** has been successfully created.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Owner", value=interaction.user.mention, inline=True)
                embed.set_footer(text="Use /balance to see your balance")
                
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed(f"something went wrong! {e}"))


    @app_commands.command(name="balance", description="Check an account's balance")
    @app_commands.describe(account_id="Account to check balance for")
    @app_commands.autocomplete(account_id=public_account_autocomplete)
    async def balance(self, interaction: discord.Interaction, account_id: str):
        try:
            account_id_int = int(account_id)
            with Session(engine) as session:
                account = session.get(Account, account_id_int)
                if not account:
                    return await interaction.response.send_message(embed=self._error_embed("Account not found."))
                
                holder_name = account.holder.name if account.holder else "Unknown"
                
                await interaction.response.send_message(discord.Embed(
                    colour=discord.Color.green(),
                    title=f"Balance for: {holder_name}",
                    description=f"**{holder_name}** has ${account.balance}"
                ))
        except ValueError:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed("Invalid account selected from autocomplete."))
        except Exception as e: 
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed(f"something went wrong! {e}"))

    @app_commands.command(name="transfer", description="Transfer credits between accounts")
    @app_commands.autocomplete(from_account=private_account_autocomplete, to_account=public_account_autocomplete)
    async def transfer(self, interaction: discord.Interaction, from_account: str, to_account: str, amount: int):
        try:
            if amount <= 0:
                return await interaction.response.send_message(embed=self._error_embed("Transfer amount must be greater than 0."))
                
            from_account_id = int(from_account)
            to_account_id = int(to_account)

            with Session(engine) as session:
                sender_account = session.get(Account, from_account_id)
                receiver_account = session.get(Account, to_account_id)
                
                if not sender_account:
                    return await interaction.response.send_message(embed=self._error_embed("Sender account not found."))
                if not receiver_account:
                    return await interaction.response.send_message(embed=self._error_embed("Receiver account not found."))
                    
                # Verify ownership of the sender account
                is_owner = False
                if sender_account.type == "CHAR" and sender_account.character_holder:
                    if sender_account.character_holder.discord_id == interaction.user.id:
                        is_owner = True
                elif sender_account.type == "BIZ" and sender_account.business_holder:
                    if sender_account.business_holder.owner and sender_account.business_holder.owner.discord_id == interaction.user.id:
                        is_owner = True
                        
                if not is_owner:
                    return await interaction.response.send_message(embed=self._error_embed("You do not have permission to transfer from this account."))
                    
                if sender_account.balance < amount:
                    return await interaction.response.send_message(embed=self._error_embed("Insufficient funds in the sender's account."))
                    
                sender_account.balance -= amount
                receiver_account.balance += amount
                
                session.commit()
                
                sender_name = sender_account.holder.name if sender_account.holder else "Unknown Sender"
                receiver_name = receiver_account.holder.name if receiver_account.holder else "Unknown Receiver"

                receiver_owner_id = None
                if receiver_account.type == "CHAR" and receiver_account.character_holder:
                    receiver_owner_id = receiver_account.character_holder.discord_id
                elif receiver_account.type == "BIZ" and receiver_account.business_holder and receiver_account.business_holder.owner:
                    receiver_owner_id = receiver_account.business_holder.owner.discord_id

                embed = discord.Embed(
                    title="Transfer Successful",
                    description=f"Transferred **${amount}** from **{sender_name}** to **{receiver_name}**.",
                    color=discord.Color.green()
                )
                
                if receiver_owner_id == interaction.user.id:
                    embed.set_footer(text="Warning: Account boosting is against the rules!")
                    
                await interaction.response.send_message(embed=embed)
        except ValueError:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed("Please select an account from the autocomplete list."))
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed(f"something went wrong! {e}"))

    @app_commands.command(name="list", description="List accounts and their balances")
    @app_commands.describe(user="Optional: The user to list accounts for")
    async def list_accounts(self, interaction: discord.Interaction, user: discord.User = None): #type:ignore
        try:
            with Session(engine) as session:
                if user:
                    char_stmt = select(Character).where(Character.discord_id == user.id).limit(25)
                    characters = session.scalars(char_stmt).all()

                    biz_stmt = select(Business).join(Business.owner).where(Character.discord_id == user.id).limit(25)
                    businesses = session.scalars(biz_stmt).all()

                    accounts = []
                    for char in characters:
                        if char.account:
                            accounts.append(char.account)
                    for biz in businesses:
                        if biz.account:
                            accounts.append(biz.account)
                    
                    accounts = accounts[:25]
                    title = f"Accounts for {user.display_name}"
                else:
                    stmt = select(Account).limit(25)
                    accounts = session.scalars(stmt).all()
                    title = "Accounts"
                
                if not accounts:
                    return await interaction.response.send_message(embed=self._error_embed("No accounts found."))
                    
                embed = discord.Embed(title=title, color=discord.Color.blue())
                for acc in accounts:
                    holder_name = acc.holder.name if acc.holder else f"Account #{acc.id}"
                    icon = "[🏢]" if acc.type == "BIZ" else "[👤]"
                    
                    owner_mention = "Unknown"
                    if acc.type == "CHAR" and acc.character_holder:
                        owner_mention = f"<@{acc.character_holder.discord_id}>"
                    elif acc.type == "BIZ" and acc.business_holder and acc.business_holder.owner:
                        owner_mention = f"<@{acc.business_holder.owner.discord_id}>"
                        
                    embed.add_field(
                        name=f"{icon} {holder_name}", 
                        value=f"**Owner:** {owner_mention}\n**Balance:** ${acc.balance}", 
                        inline=False
                    )
                    
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed(f"something went wrong! {e}"))

    @app_commands.command(name="setbalance", description="Set a user's account balance (Staff Only)")
    @app_commands.describe(account_id="Account to modify balance for", amount="New balance amount")
    @app_commands.autocomplete(account_id=public_account_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_balance(self, interaction: discord.Interaction, account_id: str, amount: int):
        """Sets a user's account balance"""
        try:
            account_id_int = int(account_id)
            with Session(engine) as session:
                account = session.get(Account, account_id_int)
                if not account:
                    return await interaction.response.send_message(embed=self._error_embed("Account not found."))
                account.balance = amount
                session.commit()
                await interaction.response.send_message(embed=discord.Embed(
                    colour=discord.Color.green(),
                    title="Balance Updated",
                    description=f"Account **{account.holder.name if account.holder else f'#{account_id_int}'}** balance set to **${amount}**."
                ))
        except ValueError:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed("Invalid account selected from autocomplete."))
        except commands.CheckFailure:
            await interaction.response.send_message(embed=self._error_embed("You do not have permission to use this command."))
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed(f"something went wrong! {e}"))


    @app_commands.command(name="delete", description="Delete a character (Staff Only)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete(self, interaction: discord.Interaction, name: str):
        """Deletes a character"""
        try:
            with Session(engine) as session:
                character = session.get(Character, name)
                if not character:
                    return await interaction.response.send_message(embed=self._error_embed(f"Character `{name}` not found."))
                
                if character.account:
                    session.delete(character.account)
                session.delete(character)
                session.commit()

                embed = discord.Embed(
                    title="Character Deleted",
                    description=f"Character **{name}** has been successfully deleted.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
        except commands.CheckFailure:
            await interaction.response.send_message(embed=self._error_embed("You do not have permission to use this command."))
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=self._error_embed(f"something went wrong! {e}"))



async def setup(bot: commands.AutoShardedBot):
    await bot.add_cog(Cog(bot))
