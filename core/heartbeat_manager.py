import asyncio
import aiohttp
import logging
from typing import Dict
from datetime import datetime

class HeartbeatManager:
    """Manages module heartbeats"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_heartbeats: Dict[str, asyncio.Task] = {}
        self.running = True
        
    async def send_heartbeat(self, name: str, url: str):
        """Send periodic heartbeats for a module"""
        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    current_time = datetime.now().timestamp()
                    full_url = f"{url}{current_time}"
                    async with session.get(full_url) as response:
                        if response.status != 200:
                            self.logger.warning(f"Heartbeat failed for {name}: {response.status}")
            except Exception as e:
                self.logger.error(f"Error sending heartbeat for {name}: {e}")
            await asyncio.sleep(60)  # Send heartbeat every minute

    def start_heartbeat(self, name: str, url: str):
        """Start heartbeat for a module"""
        if name not in self.active_heartbeats:
            self.active_heartbeats[name] = asyncio.create_task(self.send_heartbeat(name, url))
            self.logger.info(f"Started heartbeat for {name}")

    def stop_heartbeat(self, name: str):
        """Stop heartbeat for a module"""
        if name in self.active_heartbeats:
            self.active_heartbeats[name].cancel()
            del self.active_heartbeats[name]
            self.logger.info(f"Stopped heartbeat for {name}")

    def stop_all(self):
        """Stop all heartbeats"""
        self.running = False
        for name in list(self.active_heartbeats.keys()):
            self.stop_heartbeat(name)