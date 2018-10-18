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
        await client.send_msgs(hex_msg)


async def send_hex_msgs(client, hex_msgs):
    async with client:
        await client.send_hex_msgs(hex_msgs)


async def play_recording(client, file_path):
    async with client:
        await client.play_recording(file_path)
