import aiohttp, asyncio, shlex

from op import OPs as op

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
    def __init__(self, token: str, prefix: str, presence: Presence = Presence()):
        self.interval = None
        self.sequence = None
        self.session = None
        self.prefix = prefix
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
        
    def command(self):
        def wrapper(function):
        	self.commands[function.__name__] = function
        return wrapper
	
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
                    self.user = data["d"]["user"]
                    print(f'Connected to {self.user["username"]}#{self.user["discriminator"]}')

                if event == "MESSAGE_CREATE":
                    msg = data["d"]
                    content = msg["content"]
                    if "bot" not in msg["author"]:
                        msg["author"]["bot"] = False
                    
                    
                    if not msg["author"]["bot"]:
                        if content.startswith(self.prefix):
                            
                            command = shlex.split(content[len(self.prefix):])
                            if command[0] in self.commands:
                                await self.commands[command[0]](msg, *command[1:])
                                

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
                        await asyncio.gather(self.heartbeat(), self.event())
                        
                        
            except aiohttp.ClientConnectionError:
                print("Reconnecting...")
                await asyncio.sleep(5)
            finally:
                await self.ws.close()
            await asyncio.sleep(5)
    
    def run(self, bot: bool):
        self.headers = {"Authorization": f'{"Bot" if bot else "Bearer"} {self.auth["token"]}'}
        self.loop = asyncio.new_event_loop()  
        self.loop.run_until_complete(self.main())
        

client = Client("TOKEN", "!", Presence("online", Activity("Dungeon Master", 0)))

@client.command()
async def name(ctx, value1, value2):
    print(ctx, value1, value2)

client.run(True)
