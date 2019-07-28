

async def check_senders_expired(self, expiry_minutes):
    now = time.time()
    connections = list(self.clients.values())
    for conn in connections:
        if (now - conn.last_message_processed) / 60 > expiry_minutes:
            conn.connection_lost(None)
            del self.clients[conn.peer]
    await asyncio.sleep(60)

    def send(self, data: AnyStr):
        self.transport.sendto(data, addr=(self.peer_ip, self.peer_port))
