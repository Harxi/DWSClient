from aioconsole import aprint, ainput

import aiohttp, asyncio, shlex, threading
import op

class Activity:
    def __init__(self, description: str = "", type: int = 0):
        self.description = description
        self.type = 0
        
    def json(self):
        return {
            "name": self.description,
            "type": self.type
        }

class Presence:
    def __init__(self, status: str = "online", activity: Activity = Activity()):
        self.activity = activity
        self.status = status

class Client:
    def __init__(self, token, prefix: str, presence: Presence = Presence()):
        self.interval = None
        self.sequence = None
        self.session = None
        self.connected = False
        self.prefix = prefix
        self.channel = "your channel here"
        self.commands = {}
        
        self.auth = {
            "token": token,	
            "properties": {
                "$os": "linux",
                "$browser": "disco",
                "$device": "disco"
            },
            "presence": { 
                "activities": [presence.activity.json()] if presence.activity != None else [], 
            "status": presence.status,
            "afk": False
            },
            "intents": 32767
        }
        
    def opcode(self, opcode: int, payload) -> dict:
        return {
            "op": opcode,
            "d": payload
        }
    
    async def cycle(self):
        print("Waiting for connection...")
        await asyncio.sleep(self.interval / 50)
        while not self.connected:
            print("Unable to connect to the user, check validity of the token or internet connection. Waiting for connection...")
            await asyncio.sleep(self.interval / 100)
        while True:
            answer = await ainput("Write: ")
            await self.send(answer, self.channel)
	    
    async def event(self):
        async for msg in self.ws:
            data = msg.json()
            if data["op"] == op.DISPATCH:
                self.sequence = int(data["s"])
                event = data["t"]
                if event == "READY":
                    self.session = data["d"]["session_id"]
                    self.user = data["d"]["user"]
                    self.connected = True
                    await aprint(f'Connected to {self.user["username"]}#{self.user["discriminator"]}')

                if event == "MESSAGE_CREATE":
                    msg = data["d"]
                    content = msg["content"]
                    if "bot" not in msg["author"]:
                        msg["author"]["bot"] = False
                    if msg["channel_id"] == self.channel:
                        await aprint(f'[{"BOT" if msg["author"]["bot"] else "USER" }] {"YOU" if self.user["id"] == msg["author"]["id"] else msg["author"]["username"] + "#" + msg["author"]["discriminator"]} > {content}')  

    async def fetch_user(self, user: int):
        return await (await self.__session.get(f"https://discord.com/api/v9/users/{user}", headers = self.headers)).json()
    
    async def send(self, content: str, channel_id: int):
        await self.__session.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers = self.headers, json = {"content": content, "tts": "false", "flags": "0"})
                    
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
                        
                        hello = await self.ws.receive_json()
                        if hello["op"] != 10:
                            print("Received not hello")
                            return
                        self.interval = (hello["d"]["heartbeat_interval"] - 2000) / 1000
                        await asyncio.gather(self.heartbeat(), self.event(), self.cycle())
            except aiohttp.ClientConnectionError:
                print("Reconnecting...")
                await asyncio.sleep(5)
            finally:
                await self.ws.close()
                return
            await asyncio.sleep(5)
    
    def run(self, bot: bool):
        self.headers = {"Authorization": f'{"Bot" if bot else "Bearer"} {self.auth["token"]}'}
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.main())
        

client = Client("token", "!")

client.run(True)
