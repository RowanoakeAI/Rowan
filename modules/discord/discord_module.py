# modules/discord/discord_module.py
import discord
from discord.ext import commands
from typing import Dict, Any, Optional
from datetime import datetime
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
    
    async def get_prefix(self, message: discord.Message) -> str:
        """Return command prefix - always use prefix for explicit commands"""
        return DiscordConfig.COMMAND_PREFIX

    def __init__(self, rowan: RowanAssistant, memory: PersonalMemorySystem):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        # Change to use get_prefix instead of static prefix
        super().__init__(command_prefix=self.get_prefix, intents=intents)
        
        self.rowan = rowan
        self.memory = memory
        # Set up Discord-specific logger
        self.logger = setup_logger(
            'discord', 
            log_format='standard',
            max_bytes=10485760,  # 10MB
            backup_count=5,
            env='discord'  # This will create discord-specific log files
        )
        self.emoji_manager = EmojiManager(DiscordConfig.EMOJI_AND_FORMATTING_FILE)

    async def setup_hook(self):
        """Setup bot hooks and commands"""
        self.add_command(commands.Command(self.chat, name="chat"))
        self.add_command(commands.Command(self.memory_search, name="memory"))
        self.add_command(commands.Command(self.help_command, name="help"))

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
            ctx = await self.get_context(message)
            await self.chat(ctx, message=message.content)

    async def chat(self, ctx: commands.Context, *, message: str):
        """Handle chat command"""
        try:
            self.logger.info(f"Chat from {ctx.author}: {message}")
                
            # Create Discord-specific context
            discord_context = self._create_context(ctx)
            
            # Get response from Rowan
            response = self.rowan.chat(
                message,
                context_type=InteractionContext.CASUAL,
                source=InteractionSource.DISCORD
            )
            
            if len(response) > DiscordConfig.MAX_RESPONSE_LENGTH:
                response = response[:DiscordConfig.MAX_RESPONSE_LENGTH-3] + "..."
            
            # Send and log response
            await ctx.reply(response)
            self.logger.info(f"Responded to {ctx.author} with: {response[:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error in chat command from {ctx.author}: {str(e)}")
            await ctx.reply("I apologize, but I encountered an error processing your message.")

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

    async def memory_search(self, ctx: commands.Context, *, query: str):
        """Search Rowan's memory"""
        try:
            memories = self.memory.get_relevant_memories(query)
            response = "Here's what I remember:\n\n"
            
            for memory in memories.get("interactions", []):
                response += f"• {memory.get('content', {}).get('message', 'No content')}\n"
                
            await ctx.reply(response[:1900] + "..." if len(response) > 1900 else response)
            
        except Exception as e:
            self.logger.error(f"Error in memory search: {str(e)}")
            await ctx.reply("I couldn't search my memories right now.")

    async def help_command(self, ctx: commands.Context):
        """Display help information"""
        if DiscordConfig.DELETE_COMMAND_AFTER:
            await ctx.message.delete()
            
        help_text = f"""
**Rowan Discord Commands**
• `{DiscordConfig.COMMAND_PREFIX}chat <message>` - Chat with Rowan
• `{DiscordConfig.COMMAND_PREFIX}memory <query>` - Search Rowan's memories
• `{DiscordConfig.COMMAND_PREFIX}help` - Show this help message
        """
        await ctx.reply(help_text)

class DiscordModule(ModuleInterface):
    """Discord integration module for Rowan"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.client: Optional[RowanDiscordClient] = None
        self.rowan: Optional[RowanAssistant] = None
        self.memory: Optional[PersonalMemorySystem] = None
        self.token: Optional[str] = None
        
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
            self.memory = self.rowan.memory  # Use the same memory instance
            
            # Create Discord client
            self.client = RowanDiscordClient(self.rowan, self.memory)
            
            self.logger.info("Discord module initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Discord module: {str(e)}")
            return False
            
    def process(self, input_data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process input through Discord module"""
        # This method isn't used directly as Discord handles its own I/O
        return {
            "success": True,
            "message": "Discord module handles its own processing"
        }
        
    def shutdown(self) -> None:
        """Shutdown Discord module"""
        try:
            if self.client:
                import asyncio
                asyncio.create_task(self.client.close())
            self.logger.info("Discord module shut down successfully")
        except Exception as e:
            self.logger.error(f"Error shutting down Discord module: {str(e)}")