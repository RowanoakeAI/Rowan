# modules/discord/discord_module.py
# Add relative path handling for imports
from pathlib import Path
import sys
import discord
from discord.ext import commands
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import threading

from core.module_manager import ModuleInterface
from core.personal_memory import InteractionContext, PersonalMemorySystem, InteractionSource
from core.rowan_assistant import RowanAssistant
from core.memory_manager import MemoryManager
from utils.logger import setup_logger
from utils.serialization import DataSerializer
from config.discord_config import DiscordConfig
from .emoji_manager import EmojiManager

class RowanDiscordClient(commands.Bot):
    """Discord client implementation for Rowan"""
    
    def __init__(self, rowan: RowanAssistant, memory: PersonalMemorySystem):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents
        )
        
        self.rowan = rowan
        self.memory = memory
        self.logger = setup_logger(
            'discord',
            log_format='standard', 
            max_bytes=10485760,
            backup_count=5,
            env='discord'
        )
        self.emoji_manager = EmojiManager(DiscordConfig.EMOJI_AND_FORMATTING_FILE)
        self.cooldowns = commands.CooldownMapping.from_cooldown(
            rate=2, per=10.0, type=commands.BucketType.user
        )

    async def chunk_and_send(self, interaction: discord.Interaction, content: str) -> None:
        """Split and send long messages in chunks"""
        chunks = [content[i:i + DiscordConfig.MAX_RESPONSE_LENGTH] 
                 for i in range(0, len(content), DiscordConfig.MAX_RESPONSE_LENGTH)]
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(chunk)
                await asyncio.sleep(0.5)  # Rate limit prevention

    async def chat_command(self, interaction: discord.Interaction, message: str):
        """Handle chat slash command with improved error handling"""
        try:
            # Check cooldown
            bucket = self.cooldowns.get_bucket(interaction)
            retry_after = bucket.update_rate_limit()
            if (retry_after):
                await interaction.response.send_message(
                    f"Please wait {retry_after:.1f}s before using this command again.",
                    ephemeral=True
                )
                return

            await interaction.response.defer(thinking=True)
            
            async with interaction.channel.typing():
                discord_context = self._create_context_from_interaction(interaction)
                response = self.rowan.chat(
                    message,
                    context_type=InteractionContext.CASUAL,
                    source=InteractionSource.DISCORD
                )
                
                await self.chunk_and_send(interaction, response)
                self.logger.info(f"Responded to {interaction.user}: {response[:100]}...")
                
        except discord.HTTPException as e:
            self.logger.error(f"Discord API error: {str(e)}")
            await interaction.followup.send(
                "I encountered a network error. Please try again.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Error in chat command from {interaction.user}: {str(e)}")
            await interaction.followup.send(
                "I apologize, but I encountered an error processing your message.",
                ephemeral=True
            )

    def _create_context_from_interaction(self, interaction: discord.Interaction) -> Dict[str, Any]:
        """Create standardized context with proper error handling"""
        try:
            return {
                "platform": "discord",
                "channel": getattr(interaction.channel, 'name', 'Unknown'),
                "channel_id": interaction.channel_id,
                "author": str(interaction.user),
                "author_id": interaction.user.id,
                "guild": getattr(interaction.guild, 'name', 'DM'),
                "guild_id": getattr(interaction.guild, 'id', None),
                "timestamp": datetime.utcnow(),
                "locale": str(interaction.locale),
                "permissions": interaction.permissions.value
            }
        except AttributeError as e:
            self.logger.warning(f"Error creating context: {str(e)}")
            return {
                "platform": "discord",
                "timestamp": datetime.utcnow(),
                "error": "Failed to create full context"
            }

    async def get_prefix(self, message: discord.Message) -> str:
        """Return command prefix - always use prefix for explicit commands"""
        return DiscordConfig.COMMAND_PREFIX

    async def setup_hook(self):
        """Setup slash commands"""
        commands = [
            # Core commands
            discord.app_commands.Command(
                name="chat",
                description="Chat with Rowan",
                callback=self.chat_command
            ),
            discord.app_commands.Command(
                name="memory", 
                description="Search Rowan's memories",
                callback=self.memory_command
            ),
            discord.app_commands.Command(
                name="help",
                description="Show help information", 
                callback=self.help_command
            ),
            
            # Status commands
            discord.app_commands.Command(
                name="status",
                description="Check Rowan's status and uptime",
                callback=self.status_command
            ),
            discord.app_commands.Command(
                name="clear",
                description="Clear your conversation history",
                callback=self.clear_command
            ),
            discord.app_commands.Command(
                name="settings",
                description="View or modify your preferences",
                callback=self.settings_command
            ),

            # Memory management
            discord.app_commands.Command(
                name="remember",
                description="Create a new memory",
                callback=self.remember_command
            ),
            discord.app_commands.Command(
                name="forget",
                description="Delete specific memories",
                callback=self.forget_command
            ),
            discord.app_commands.Command(
                name="stats",
                description="View memory statistics",
                callback=self.stats_command
            ),

            # Module features  
            discord.app_commands.Command(
                name="calendar",
                description="Access calendar features",
                callback=self.calendar_command
            ),
            discord.app_commands.Command(
                name="notes",
                description="Create and manage notes",
                callback=self.notes_command
            ),
            discord.app_commands.Command(
                name="remind",
                description="Set reminders",
                callback=self.remind_command
            )
        ]

        # Add commands to the command tree
        for cmd in commands:
            self.tree.add_command(cmd)

        try:
            # Sync to each guild individually
            for guild in self.guilds:
                try:
                    await self.tree.sync(guild=guild)
                    self.logger.info(f"Synced commands to guild: {guild.name} ({guild.id})")
                    await asyncio.sleep(2)  # Rate limiting
                except discord.HTTPException as e:
                    self.logger.error(f"Failed to sync commands to guild {guild.name}: {e}")
                    
            self.logger.info("Completed syncing commands to all guilds")
            
        except Exception as e:
            self.logger.error(f"Error during guild-specific sync: {e}")
            # Fallback to global sync
            await self.tree.sync(guild=None)
            self.logger.info("Fallback: Synced commands globally")

    async def on_ready(self):
        """Handle bot ready event"""
        self.logger.info(f"Discord bot logged in as {self.user}")
        
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        if message.author == self.user:
            return

        # Log message received
        self.logger.debug(f"Message from {message.author} in {message.guild}/{message.channel}: {message.content[:100]}...")

        # First check if it's a command
        if message.content.startswith(DiscordConfig.COMMAND_PREFIX):
            await self.process_commands(message)
            return

        # If in main server and not a command, treat as chat
        if message.guild and message.guild.id == DiscordConfig.MAIN_SERVER_ID:
            try:
                # Create context for the message
                discord_context = {
                    "platform": "discord",
                    "channel": message.channel.name,
                    "channel_id": message.channel.id,
                    "author": str(message.author),
                    "author_id": message.author.id,
                    "guild": message.guild.name if message.guild else "DM",
                    "guild_id": message.guild.id if message.guild else None,
                    "timestamp": datetime.utcnow()
                }

                # Use the rowan instance to handle the chat
                response = self.rowan.chat(
                    message.content,
                    context_type=InteractionContext.CASUAL,
                    source=InteractionSource.DISCORD
                )

                # Send response in chunks if needed
                if len(response) > DiscordConfig.MAX_RESPONSE_LENGTH:
                    chunks = [response[i:i + DiscordConfig.MAX_RESPONSE_LENGTH] 
                             for i in range(0, len(response), DiscordConfig.MAX_RESPONSE_LENGTH)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                        await asyncio.sleep(0.5)  # Rate limit prevention
                else:
                    await message.channel.send(response)

            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                await message.channel.send("I encountered an error processing your message.")

    async def status_command(self, interaction: discord.Interaction):
        """Show Rowan's status"""
        await interaction.response.send_message(f"Status: Online\nUptime: {self.rowan.get_uptime()}")

    async def clear_command(self, interaction: discord.Interaction):
        """Clear conversation history"""
        await interaction.response.defer()
        self.memory.clear_user_history(str(interaction.user.id))
        await interaction.followup.send("Conversation history cleared!")

    async def settings_command(self, interaction: discord.Interaction):
        """Manage user settings"""
        # TODO: Implement settings management
        await interaction.response.send_message("Settings management coming soon!")

    async def remember_command(self, interaction: discord.Interaction, content: str):
        """Create new memory"""
        await interaction.response.defer()
        self.memory.add_memory(content, str(interaction.user.id))
        await interaction.followup.send("Memory stored!")

    async def forget_command(self, interaction: discord.Interaction, query: str):
        """Delete memories matching query"""
        await interaction.response.defer()
        deleted = self.memory.delete_memories(query, str(interaction.user.id))
        await interaction.followup.send(f"Deleted {deleted} memories matching your query.")

    async def stats_command(self, interaction: discord.Interaction):
        """Show memory statistics"""
        stats = self.memory.get_stats()
        await interaction.response.send_message(f"Memory stats:\n{stats}")

    async def calendar_command(self, interaction: discord.Interaction, action: str, *args):
        """Handle calendar operations"""
        # TODO: Implement calendar integration
        await interaction.response.send_message("Calendar features coming soon!")

    async def notes_command(self, interaction: discord.Interaction, action: str, *args):
        """Manage notes"""
        # TODO: Implement notes system
        await interaction.response.send_message("Notes system coming soon!")

    async def remind_command(self, interaction: discord.Interaction, time: str, message: str):
        """Set reminders"""
        # TODO: Implement reminder system
        await interaction.response.send_message("Reminder system coming soon!")

    def _create_context(self, ctx: commands.Context) -> Dict[str, Any]:
        """Create standardized context from Discord context"""
        return {
            "platform": "discord",
            "channel": ctx.channel.name,
            "channel_id": ctx.channel.id,
            "author": str(ctx.author),
            "author_id": ctx.author.id,
            "guild": ctx.guild.name if ctx.guild else "DM",
            "guild_id": ctx.guild.id if ctx.guild else None,
            "timestamp": datetime.utcnow()
        }

    async def memory_command(self, interaction: discord.Interaction, query: str):
        """Handle memory slash command"""
        try:
            await interaction.response.defer()
            
            memories = self.memory.get_relevant_memories(query)
            response = "Here's what I remember:\n\n"
            
            for memory in memories.get("interactions", []):
                response += f"• {memory.get('content', {}).get('message', 'No content')}\n"
                
            await interaction.followup.send(response[:1900] + "..." if len(response) > 1900 else response)
            
        except Exception as e:
            self.logger.error(f"Error in memory search: {str(e)}")
            await interaction.followup.send("I couldn't search my memories right now.")

    async def help_command(self, interaction: discord.Interaction):
        """Show help information"""
        help_text = """
**Rowan Discord Commands**

Core Commands:
• `/chat <message>` - Chat with Rowan
• `/memory <query>` - Search Rowan's memories
• `/help` - Show this help message
• `/status` - Check Rowan's status
• `/clear` - Clear conversation history
• `/settings` - Manage preferences

Memory Management:
• `/remember <content>` - Create new memory
• `/forget <query>` - Delete memories
• `/stats` - View memory statistics

Module Features:
• `/calendar` - Calendar features
• `/notes` - Notes system
• `/remind` - Set reminders
    """
        await interaction.response.send_message(help_text)

class DiscordModule(ModuleInterface):
    """Discord integration module for Rowan"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.client: Optional[RowanDiscordClient] = None
        self.rowan: Optional[RowanAssistant] = None
        self.memory: Optional[PersonalMemorySystem] = None
        self.token: Optional[str] = None
        self.bot_thread: Optional[threading.Thread] = None
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize Discord module"""
        try:
            # Validate config
            if not DiscordConfig.validate():
                raise ValueError("Invalid Discord configuration")

            # Store token
            self.token = DiscordConfig.DISCORD_TOKEN
            if not self.token:
                raise ValueError("Discord token not found in configuration")
                
            # Use existing Rowan instance from config
            self.rowan = config["rowan"]
            self.memory = self.rowan.memory
            
            # Create Discord client
            self.client = RowanDiscordClient(self.rowan, self.memory)
            
            # Start bot in separate thread
            self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
            self.bot_thread.start()
            
            self.logger.info("Discord module initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Discord module: {str(e)}")
            return False

    def _run_bot(self):
        """Run the Discord bot in its own thread"""
        try:
            asyncio.run(self.client.start(self.token))
        except Exception as e:
            self.logger.error(f"Error running Discord bot: {str(e)}")

    def process(self, input_data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process input through Discord module"""
        # This method isn't used directly as Discord handles its own I/O
        return {
            "success": True,
            "message": "Discord module handles its own processing"
        }
        
    def _run_coroutine(self, coroutine):
        """Helper method to run coroutines in the current event loop"""
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a future and run it
                return asyncio.create_task(coroutine)
            else:
                # If loop isn't running, run the coroutine directly
                return loop.run_until_complete(coroutine)
        except RuntimeError:
            # If no event loop exists in thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()
                
    def shutdown(self) -> None:
        """Shutdown Discord module"""
        try:
            if self.client:
                # Close the client
                self._run_coroutine(self.client.close())
                
            # Wait for bot thread to end
            if self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=5)
                
            self.logger.info("Discord module shut down successfully")
        except Exception as e:
            self.logger.error(f"Error shutting down Discord module: {str(e)}")