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
        """Autocomplete for accounts using TYPE-ID format. Scoped based on command context."""
        with Session(engine) as session:
            # Check if we need private (owned) or public (all) accounts
            is_private = (
                interaction.command.name == "transfer" and 
                interaction.focused.name == "from_account"
            )

            if is_private:
                # Get accounts owned by the user's characters
                stmt = (
                    select(Account)
                    .join(Character)
                    .where(Character.discord_id == interaction.user.id)
                )
            else:
                # Public: All accounts
                stmt = select(Account)

            # Filter by typing
            if current:
                # User might type "ACC-1" or just "1"
                if "-" in current:
                    acc_type, acc_id = current.split("-", 1)
                    stmt = stmt.where(Account.type.ilike(f"{acc_type}%"))
                    if acc_id.isdigit():
                        stmt = stmt.where(Account.id == int(acc_id))
                elif current.isdigit():
                    stmt = stmt.where(Account.id == int(current))
                else:
                    stmt = stmt.where(Account.type.ilike(f"{current}%"))

            results = session.scalars(stmt.limit(25)).all()
            
            choices = []
            for acc in results:
                # Find the primary owner name for the label
                owner = session.scalar(select(Character.name).where(Character.account_id == acc.id))
                label = f"{acc.type}-{acc.id}"
                if owner:
                    label += f" ({owner})"
                
                choices.append(app_commands.Choice(name=label, value=f"{acc.type}-{acc.id}"))
            
            return choices

    @app_commands.command(name="create", description="Create a new character")
    async def create(self, interaction: discord.Interaction, name: str):
        """Creates a new character and an associated account."""
        with Session(engine) as session:
            existing_char = session.get(Character, name)
            if existing_char:
                await interaction.response.send_message(f"Character `{name}` already exists.", ephemeral=True)
                return

            # Default type 'ACC' for character accounts
            new_account = Account(type="ACC", balance=0)
            session.add(new_account)
            session.flush()

            new_char = Character(
                name=name, 
                discord_id=interaction.user.id, 
                account_id=new_account.id
            )
            session.add(new_char)
            session.commit()

        await interaction.response.send_message(f"Character `{name}` created with Account: **ACC-{new_account.id}**")

    @app_commands.command(name="balance", description="Check an account's balance")
    @app_commands.autocomplete(account=account_autocomplete)
    async def balance(self, interaction: discord.Interaction, account: str):
        """Check balance using TYPE-ID (Public)."""
        if "-" not in account:
            await interaction.response.send_message("Invalid account format. Use `TYPE-ID` (e.g., ACC-1).", ephemeral=True)
            return

        acc_type, acc_id_str = account.split("-", 1)
        try:
            acc_id = int(acc_id_str)
        except ValueError:
            await interaction.response.send_message("Invalid Account ID.", ephemeral=True)
            return

        with Session(engine) as session:
            acc = session.scalar(select(Account).where(Account.id == acc_id, Account.type == acc_type))
            if not acc:
                await interaction.response.send_message(f"Account `{account}` not found.", ephemeral=True)
                return
            
            await interaction.response.send_message(f"Account **{account}** balance: **{acc.balance}** credits.")

    @app_commands.command(name="transfer", description="Transfer credits between accounts")
    @app_commands.autocomplete(from_account=account_autocomplete, to_account=account_autocomplete)
    async def transfer(self, interaction: discord.Interaction, from_account: str, to_account: str, amount: int):
        """Transfer between accounts using TYPE-ID."""
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        if "-" not in from_account or "-" not in to_account:
            await interaction.response.send_message("Invalid account format. Use `TYPE-ID`.", ephemeral=True)
            return

        f_type, f_id_str = from_account.split("-", 1)
        t_type, t_id_str = to_account.split("-", 1)

        with Session(engine) as session:
            # Ownership check: User must own a character that owns the from_account
            owner_check = session.scalar(
                select(Character).where(
                    Character.account_id == int(f_id_str), 
                    Character.discord_id == interaction.user.id
                )
            )
            if not owner_check:
                await interaction.response.send_message(f"You do not own Account `{from_account}`.", ephemeral=True)
                return

            sender_acc = session.scalar(select(Account).where(Account.id == int(f_id_str), Account.type == f_type))
            receiver_acc = session.scalar(select(Account).where(Account.id == int(t_id_str), Account.type == t_type))

            if not sender_acc or not receiver_acc:
                await interaction.response.send_message("One or both accounts not found.", ephemeral=True)
                return

            if sender_acc.balance < amount:
                await interaction.response.send_message(f"Insufficient funds in `{from_account}`.", ephemeral=True)
                return

            sender_acc.balance -= amount
            receiver_acc.balance += amount
            session.commit()

        await interaction.response.send_message(f"Transferred **{amount}** from **{from_account}** to **{to_account}**.")

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

async def setup(bot: commands.AutoShardedBot):
    await bot.add_cog(Cog(bot))
