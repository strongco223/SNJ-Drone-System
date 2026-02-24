def calc_crc(data: bytes) -> int:
    crc = 0x00
    poly = 0xD5

    for byte in data:
        crc ^= byte  # XOR 每個位元組
        for _ in range(8):  # 每個位元處理 8 次
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF  # 限制在 8 bit 範圍
            else:
                crc = (crc << 1) & 0xFF
    return crc