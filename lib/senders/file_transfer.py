import asyncio
import asyncssh
import sys


async def start_server():
    await asyncssh.listen('127.0.0.1', 8022,
                          sftp_factory=True)

loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(start_server())
except (OSError, asyncssh.Error) as exc:
    sys.exit('Error starting server: ' + str(exc))

loop.run_forever()
