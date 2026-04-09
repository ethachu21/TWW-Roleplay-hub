import discord
from discord.ext import commands
from discord import app_commands
from Data.tables import Character, Account
from Data import engine
from sqlalchemy.orm import Session
from sqlalchemy import select

class Cog(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot) -> None:
        super().__init__()
        self.bot = bot

    async def account_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete for accounts based ONLY on character name."""
        with Session(engine) as session:
            # Determine if we need to filter by the user's own characters
            is_private = (
                interaction.command.name == "transfer" and 
                interaction.focused.name == "from_account"
            )

            stmt = select(Character)
            if is_private:
                stmt = stmt.where(Character.discord_id == interaction.user.id)

            if current:
                stmt = stmt.where(Character.name.ilike(f"%{current}%"))

            # Limit results for performance and Discord constraints
            results = session.scalars(stmt.limit(25)).all()
            
            choices = []
            for char in results:
                acc = session.get(Account, char.account_id)
                if not acc:
                    continue
                
                # Label: Name (TYPE-ID), Value: TYPE-ID
                label = f"{char.name} ({acc.type}-{acc.id})"
                choices.append(app_commands.Choice(name=label, value=f"{acc.type}-{acc.id}"))
            
            return choices

    @app_commands.command(name="create", description="Create a new character")
    async def create(self, interaction: discord.Interaction, name: str):
        """Creates a new character and an associated account."""
        with Session(engine) as session:
            existing_char = session.get(Character, name)
            if existing_char:
                return await interaction.response.send_message(f"Character `{name}` already exists.", ephemeral=True)

            # Default type 'ACC' for character accounts with 1000 starting credits
            new_account = Account(type="ACC", balance=1000)
            session.add(new_account)
            session.flush()

            new_char = Character(
                name=name, 
                discord_id=interaction.user.id, 
                account_id=new_account.id
            )
            session.add(new_char)
            session.commit()

            embed = discord.Embed(
                title="Character Created",
                description=f"Character **{name}** has been successfully created.",
                color=discord.Color.green()
            )
            embed.add_field(name="Account ID", value=f"ACC-{new_account.id}", inline=True)
            embed.add_field(name="Owner", value=interaction.user.mention, inline=True)
            embed.set_footer(text="Starting Balance: 1,000 credits")
            
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description="Check an account's balance")
    async def balance(self, interaction: discord.Interaction, account: str):
        """Check balance using TYPE-ID (Public)."""
        if "-" not in account:
            return await interaction.response.send_message("Invalid account format. Please select from the autocomplete or use `TYPE-ID` (e.g., ACC-1).", ephemeral=True)

        acc_type, acc_id_str = account.split("-", 1)
        try:
            acc_id = int(acc_id_str)
        except ValueError:
            return await interaction.response.send_message("Invalid Account ID format. The ID must be a number.", ephemeral=True)

        with Session(engine) as session:
            acc = session.scalar(select(Account).where(Account.id == acc_id, Account.type == acc_type))
            if not acc:
                return await interaction.response.send_message(f"Account `{account}` not found.", ephemeral=True)
            
            # Find the character name for better UX
            char_name = session.scalar(select(Character.name).where(Character.account_id == acc.id))
            owner_str = f" (**{char_name}**)" if char_name else ""
            
            await interaction.response.send_message(f"Account **{account}**{owner_str} balance: **{acc.balance:,}** credits.")

    @balance.autocomplete("account")
    async def balance_account_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.account_autocomplete(interaction, current)

    @app_commands.command(name="transfer", description="Transfer credits between accounts")
    async def transfer(self, interaction: discord.Interaction, from_account: str, to_account: str, amount: int):
        """Transfer between accounts using TYPE-ID."""
        if amount <= 0:
            return await interaction.response.send_message("The transfer amount must be greater than zero.", ephemeral=True)

        if "-" not in from_account or "-" not in to_account:
            return await interaction.response.send_message("Invalid account format. Please use the autocomplete options.", ephemeral=True)

        f_type, f_id_str = from_account.split("-", 1)
        t_type, t_id_str = to_account.split("-", 1)

        with Session(engine) as session:
            try:
                f_id = int(f_id_str)
                t_id = int(t_id_str)
            except ValueError:
                return await interaction.response.send_message("Invalid Account ID format.", ephemeral=True)

            # Ownership check: User must own a character that owns the from_account
            owner_check = session.scalar(
                select(Character).where(
                    Character.account_id == f_id, 
                    Character.discord_id == interaction.user.id
                )
            )
            if not owner_check:
                return await interaction.response.send_message(f"You do not have permission to transfer from Account `{from_account}`.", ephemeral=True)

            sender_acc = session.scalar(select(Account).where(Account.id == f_id, Account.type == f_type))
            receiver_acc = session.scalar(select(Account).where(Account.id == t_id, Account.type == t_type))

            if not sender_acc:
                return await interaction.response.send_message(f"Source account `{from_account}` not found.", ephemeral=True)
            if not receiver_acc:
                return await interaction.response.send_message(f"Destination account `{to_account}` not found.", ephemeral=True)

            if sender_acc.balance < amount:
                return await interaction.response.send_message(f"Insufficient funds in `{from_account}`. Available: **{sender_acc.balance}**.", ephemeral=True)

            sender_acc.balance -= amount
            receiver_acc.balance += amount
            session.commit()

        await interaction.response.send_message(f"Successfully transferred **{amount:,}** from **{from_account}** to **{to_account}**.")


    @transfer.autocomplete("from_account")
    @transfer.autocomplete("to_account")
    async def transfer_account_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.account_autocomplete(interaction, current)


    @app_commands.command(name="list", description="List accounts owned by a user")
    async def list_accounts(self, interaction: discord.Interaction, user: discord.Member = None):
        """Lists accounts associated with a user's characters."""
        target = user or interaction.user
        with Session(engine) as session:
            chars = session.scalars(select(Character).where(Character.discord_id == target.id)).all()
            
            if not chars:
                await interaction.response.send_message(f"{target.display_name} has no characters/accounts.", ephemeral=True)
                return
            
            lines = []
            for c in chars:
                acc = session.get(Account, c.account_id)
                lines.append(f"- **{c.name}**: {acc.type}-{acc.id} (Balance: {acc.balance})")
            
            embed = discord.Embed(
                title=f"Accounts for {target.display_name}", 
                description="\n".join(lines), 
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

async def setup(bot: commands.AutoShardedBot):
    await bot.add_cog(Cog(bot))
