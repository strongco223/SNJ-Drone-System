from crc import calc_crc

class packet_builder:
    
    @staticmethod
    def _build_packet(data: bytes,header: int=0xAA)->bytes:
        packet_len = 2 + len(data) + 1
        packet_no_crc = bytes([header]) + bytes([packet_len]) + data
        crc_result = calc_crc(packet_no_crc)
        return packet_no_crc + bytes([crc_result])

    @staticmethod
    def get_camera_version():
        return packet_builder._build_packet(bytes([0x00,0x01]))
    
    @staticmethod
    def get_version_number():
        return packet_builder._build_packet(bytes([0x00,0x02]))
    
    @staticmethod
    def get_camera_mode():
        return packet_builder._build_packet(bytes([0x00,0x03]))
    
    @staticmethod
    def do_take_photo():
        return packet_builder._build_packet(bytes([0x01,0x04]))
    
    @staticmethod
    def do_zoom_in():
        return packet_builder._build_packet(bytes([0x01,0x0A,0x01]))
    
    @staticmethod
    def do_zoom_out():
        return packet_builder._build_packet(bytes([0x01,0x0A,0x02]))
    
    @staticmethod
    def do_center():
        return packet_builder._build_packet(bytes([0x05,0x02]))
    
    @staticmethod
    def do_joystick(pan: int ,tilt: int)->bytes:
        def clamp_128(value: int):
            return max(-128, min(128, int(value)))
        pan_bytes = clamp_128(pan).to_bytes(2, byteorder='big', signed=True)
        tilt_bytes = clamp_128(tilt).to_bytes(2, byteorder='big', signed=True)
        return packet_builder._build_packet(bytes([0x05,0x06]) + pan_bytes + tilt_bytes)
    
    @staticmethod
    def do_angle(pan: int, tilt: int, roll: int, slow_speed: bool=False)->bytes:
        def clamp_1450(value: int):
            return max(-1450, min(1450, int(value)))
        
        def clamp_900(value: int):
            return max(-900, min(900, int(value)))
        
        def clamp_400(value: int):
            return max(-400, min(400, int(value)))
            
        pan_bytes = clamp_1450(pan).to_bytes(2, byteorder='big', signed=True)
        roll_bytes = clamp_400(roll).to_bytes(2, byteorder='big', signed=True)
        tilt_bytes = clamp_900(tilt).to_bytes(2, byteorder='big', signed=True)
        speed_bytes = bytes([0x01]) if  slow_speed else bytes([0x00])
        
        return packet_builder._build_packet(bytes([0x05,0x06]) + pan_bytes + tilt_bytes + roll_bytes + speed_bytes)
