async def send_msg(client, msg):
    async with client:
        await client.send_msg(msg)


async def send_msgs(client, msgs):
    async with client:
        await client.send_msgs(msgs)


async def encode_send_msg(client, msg):
    async with client:
        await client.encode_and_send_msg(msg)


async def encode_send_msgs(client, msgs):
    async with client:
        await client.encode_and_send_msgs(msgs)


async def send_hex(client, hex_msg):
    async with client:
        await client.send_hex(hex_msg)


async def send_hex_msgs(client, hex_msgs):
    async with client:
        await client.send_hex_msgs(hex_msgs)


async def send_repeated_msg(client, hex_msg, num=1000, interval=0.001):
    import binascii
    import asyncio
    msg = binascii.unhexlify(hex_msg)
    async with client:
        for i in range(0, num):
            await client.send_msg(msg)
            await asyncio.sleep(interval)
        await asyncio.sleep(3)


async def send_incremented_msgs(client, num=1000, interval=0.001):
    import asyncio
    async with client:
        for i in range(0, num):
            msg = bytes(str(i), 'utf-8')
            await client.send_msg(msg)
            await asyncio.sleep(interval)
        await asyncio.sleep(3)


async def play_recording(client, file_path):
    async with client:
        await client.play_recording(file_path)
