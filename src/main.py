import aiohttp, asyncio
import op

class Presence:
    def __init__(self, description: str = "", status: str = "online"):
        self.description = description
        self.status = status
	
    def json(self):
        return {
            "presence": { 
            "activities": [{
                "name": self.description,
                "type": 0 
            }], 
            "status": self.status,
            "afk": False
            }
        }

class Client:
    def __init__(self, token, presence: Presence = None):
        self.interval = None
        self.sequence = None
        self.session = None
        
        self.auth = {
            "token": token,	
            "properties": {
                "$os": "linux",
                "$browser": "disco",
                "$device": "disco"
            },
            "intents": 32767
        } | presence.json() if isinstance(presence, Presence) else {}

    def opcode(self, opcode: int, payload) -> dict:
        return {
            "op": opcode,
            "d": payload
        }
            
    async def event(self):
        async for msg in self.ws:
            data = msg.json()
            if data["op"] == op.DISPATCH:
                self.sequence = int(data["s"])
                event = data["t"]
                if event == "READY":
                    self.session = data["d"]["session_id"]
                    self.id = data["d"]["user"]["id"]
                    self.bot = data["d"]["user"]["bot"]
                    
                if event == "MESSAGE_CREATE":
                    content = data["d"]["content"]
                    id = data["d"]["author"]["id"]
                    if id != self.id:
                        await self.send("Hi", data['d']['channel_id'])
    
    async def send(self, content: str, channel_id: int):
    	await self.__session.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers = {"Authorization": f'{"Bot" if self.bot else "Bearer"} {self.auth["token"]}'}, json = {"content": content, "tts": "false", "flags": "0"})
                    
    async def heartbeat(self):
        while self.interval is not None:
            await self.ws.send_json(self.opcode(op.HEARTBEAT, self.sequence))
            await asyncio.sleep(self.interval)
    
    async def main(self):
        while True:
            try:
                async with aiohttp.ClientSession() as self.__session:
                    async with self.__session.ws_connect("wss://gateway.discord.gg/?v=9&encoding=json", max_msg_size = None) as self.ws:
                        await self.ws.send_json(self.opcode(op.IDENTIFY, self.auth))
                        await asyncio.gather(self.heartbeat(), self.event())
                        
            except aiohttp.ClientConnectionError:
                print("Reconnecting...")
                await asyncio.sleep(5)
            finally:
                await self.ws.close()
            await asyncio.sleep(5)
    
    def run(self):
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.main())
