# base
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import yaml
import time
from threading import Thread
import threading

# streamer
import gi
from gi.repository import Gst, GLib
gi.require_version('Gst', '1.0')

# ai
import numpy as np
import cv2
from ultralytics import YOLO

# api
import socket
import json

# gimbal
from packet import packet_builder

model = YOLO("yolo11n.engine")
output_fps = 30
frame_duration = 1 / output_fps * Gst.SECOND  # 30fps
frame_count = 0
start_time = 0;
global bounding_boxes_json


lock_id = -1
lock_xyxy = []
locked = False



class rtsp_ai_pipline:
    def __init__(self, rtsp_src_url):
        
        '''
        self.pipeline_str = (
        f"rtspsrc location={rtsp_src_url} latency=50 ! "
        "rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw, format=RGBA ! "
        "videorate ! video/x-raw, framerate=5/1 ! "
        "tee name=t "
        "t. ! queue ! appsink name=mysink emit-signals=true sync=false max-buffers=1 drop=true "
        #"t. ! queue ! nveglglessink sync=false"
        )
        '''

        self.pipeline_str = (
        f"rtspsrc location={rtsp_src_url} latency=0 ! "
        "rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw,format=BGRx ! "
        "queue max-size-buffers=1 leaky=downstream ! "
        "appsink name=mysink emit-signals=true sync=false max-buffers=1 drop=true"
        )


        self.lasttime = time.time()
        self._parsePipeline()
    def _parsePipeline(self):
        self.pipeline = Gst.parse_launch(self.pipeline_str)
        self.appsink = self.pipeline.get_by_name("mysink")
        
        #appsink.set_property("emit-signals", True)
        #appsink.set_property("sync", False)
        #appsink.set_property("max-buffers", 1)
        #appsink.set_property("drop", True)
        #appsink.set_property("enable-last-sample", False)
        #appsink.set_property("wait-on-eos", False)
        
        self.appsink.connect("new-sample", self.on_new_sample)
        
        # 監聽 bus 訊息
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)
        
        pass
    def setStart(self):
        if self.pipeline != None:
            self.pipeline.set_state(Gst.State.PLAYING)
        else:
            print("pipeline not init")
    def setNull(self):
        if self.pipeline != None:
            self.pipeline.set_state(Gst.State.NULL)
            del self.pipeline
        else:
            print("pipeline not init")
    def schedule_reconnect(self):
        if (time.time() - self.lasttime > 10):
            self.setNull()
            self._parsePipeline()
            self.setStart()
            self.lasttime = time.time()
            print("reconnect")
    def on_bus_message(self, bus, message):
        msg_type = message.type
        #print(f"{msg_type}")
        if msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"❌ GStreamer Error: {err}, {debug}")
            self.schedule_reconnect()

        elif msg_type == Gst.MessageType.EOS:
            print("📴 End of stream (EOS)")
            self.schedule_reconnect()
    def draw_custom(self,results, frame):
        """
        自訂繪製 YOLOv11 tracking 結果在影像上。
        Args:
            results: YOLOv11 的輸出 (model.track 或 model.predict)
            frame: 原始影像 (BGR numpy array)
        Returns:
            繪製後影像 (BGR)
        """
        global lock_id, lock_xyxy, locked

        boxes = results[0].boxes
        xyxy = boxes.xyxy.cpu().numpy()         # [x1, y1, x2, y2]
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)
        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy)
        
        if lock_id in ids:
            locked = True
        else:
            locked = False

        height, width = frame.shape[:2]
        for i in range(len(xyxy)):
            x1, y1, x2, y2 = map(int, xyxy[i])
            conf = confs[i]
            cls = clss[i]
            obj_id = ids[i] if ids[i] is not None else -1

            color = (255, 0, 0)

            if lock_id == obj_id:
                color = (0, 255, 0)
                lock_xyxy = [(x1+x2)/2/width,(y1+y2)/2/height]
                print(f"x,y:{lock_xyxy}")


            label = f"ID:{obj_id} {results[0].names[cls]} {conf:.2f}"

            # 繪製邊框與標籤
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

            # 畫出矩形當文字底色（位於框內上方）
            cv2.rectangle(frame,
                (x1, y1),
                (x1 + text_w + 6, y1 + text_h + 6),
                color,  # 也可以用固定顏色 (0,0,0)
                -1)     # -1 表示填滿

            # 再畫文字
            cv2.putText(frame, label, (x1 + 3, y1 + text_h + 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    def extract_frame_from_sample(self,sample):
        """GStreamer sample -> NumPy frame"""
        buf = sample.get_buffer()
        caps = sample.get_caps().get_structure(0)
        width = caps.get_value("width")
        height = caps.get_value("height")

        success, map_info = buf.map(Gst.MapFlags.READ)
        if not success:
            return None
        try:
            frame = np.frombuffer(map_info.data, np.uint8).reshape((height, width, 4))
        finally:
            buf.unmap(map_info)
        return frame

    def on_new_sample(self,sink):
        
        in_start_time = time.time()

        #global model
        global frame_duration
        global frame_count
        global appsrc
        global start_time
        global bounding_boxes_json
        """拉一幀並顯示"""
        while True:
            tmp = sink.emit("try-pull-sample", 0)
            
            if tmp is None:
                break
            sample = tmp
        
    
        frame = self.extract_frame_from_sample(sample)
        del sample

        if frame is not None:
            #frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            frame_bgr = frame[:, :, :3]
            resized_frame = cv2.resize(frame_bgr, (960, 544))
            # (960, 540) # tensorRT (960,544)
            resized_frame = resized_frame[:,:,:3]
            
            start_infer = time.time()
            results = model.track(resized_frame,persist=True, verbose=False,classes=[0,2])
            end_infer = time.time()
            bounding_boxes_json = self.detections_to_json(results)
            annotated = self.draw_custom(results,resized_frame)
            #annotated = results[0].plot()

            
            now = time.localtime()
            timestamp = time.strftime("%M:%S", now)

            #cv2.putText(resized_frame, f"Time: {timestamp}", (10, 30),cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            now = time.time()
            localtime = time.localtime(now)
            timestamp = time.strftime("%M:%S", localtime)
            milliseconds = int((now % 1) * 1000)

            
            #data = resized_frame.tobytes()
            data = annotated.tobytes()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            
            buf.pts = buf.dts = int(frame_count * frame_duration)
            buf.duration = int(frame_duration)

            retval = appsrc.emit("push-buffer", buf)
            

            #if retval != Gst.FlowReturn.OK:
            #    print("❌ 推送失敗", retval)
            
            frame_count += 1
            end_time = time.time()
            in_end_time = time.time()
            fps = 1/(end_time - start_time)
            infer_time = (end_infer - start_infer)*1000
            handle_time = (in_end_time - in_start_time)*1000
            start_time = end_time
            print(f"output fps：{fps:.1f}")
            print(f"cycle time:{handle_time:.1f} ms")
            print(f"ai time：{infer_time:.1f} ms")

            

        return Gst.FlowReturn.OK

    def detections_to_json(self, results):
        """
        Convert YOLOv11 tracking results into:
        {"1":[x,y,w,h,0], "2":[x,y,w,h,0]}
        """
        global lock_id
        
        if not results or len(results) == 0 or results[0].boxes is None:
            return "{}"   # 空字典格式

        boxes = results[0].boxes

        xyxy = boxes.xyxy.cpu().numpy()   # [[x1,y1,x2,y2], ...]
        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy)
        classes = boxes.cls.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()

        output = {}

        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i]

            # --- 轉 xyxy → xywh --- (540p-->720p)
            x = int(x1*2)
            y = int(y1*2)
            w = int((x2 - x1)*2)
            h = int((y2 - y1)*2)

            track_id = str(ids[i]) if ids[i] is not None else str(i)

            # 塞入格式 [x,y,w,h,0]

            target = 1 if ids[i] == lock_id else 0

            output[track_id] = [x, y, w, h, target]

        return json.dumps(output)



class udp_pipline:
    def __init__(self, udp_sink_ip,udp_sink_port,output_fps):
        self.pipeline_str = (
        "appsrc name=mysrc is-live=true format=time block=true ! queue max-size-buffers=3 leaky=downstream ! videoconvert ! "
        "x264enc tune=zerolatency bitrate=2000 speed-preset=superfast ! "
        "rtph264pay config-interval=1 pt=96 ! "
        f"udpsink sync=false async=false host={udp_sink_ip} port={udp_sink_port}"
        )
        '''
        appsrc is-live=true format=time block=true !
        queue max-size-buffers=3 leaky=downstream !
        videoconvert !
        x264enc tune=zerolatency bitrate=2000 speed-preset=superfast !
        rtph264pay config-interval=1 pt=96 !
        udpsink sync=false async=false
        '''

        self.lasttime = time.time()
        self._parsePipeline()
    def _parsePipeline(self):
        self.pipeline = Gst.parse_launch(self.pipeline_str)
        self.appsrc = self.pipeline.get_by_name("mysrc")
        caps = Gst.Caps.from_string(f"video/x-raw,format=BGR,width=960,height=544,framerate={output_fps:.0f}/1")
        self.appsrc.set_property("caps", caps)
        self.appsrc.set_property("format", Gst.Format.TIME)
    def setStart(self):
        if self.pipeline != None:
            self.pipeline.set_state(Gst.State.PLAYING)
        else:
            print("pipeline not init")

class AI_Control_Server:
    def __init__(self, ip="0.0.0.0", port=10000):
        # 建立 TCP 伺服器
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((ip, port))
        self.server_sock.listen(5)    # 同時最多 5 個 client

        print(f"✅ TCP Server listening on {ip}:{port}")

        self.clients = {}            # { addr: conn }
        self.client_threads = {}     # { addr: handler_thread }
        self.lock = threading.Lock()

        self.running = True


    # ----------------------------------------------------
    # 處理 client 指令
    # ----------------------------------------------------
    def handle_command(self, data, conn, addr):
        global lock_id

        try:
            cmd = json.loads(data.decode())
            action = cmd.get("action", "")
            params = cmd.get("params", {})

            print(f"📩 Command from {addr}: {action}, params={params}")

            if action == "lock":
                lock_id = params
                response = {"status": "ok", "message": f"Locked {params}"}

            elif action == "stop":
                response = {"status": "ok", "message": "AI stopped"}

            elif action == "set_param":
                response = {"status": "ok", "message": f"Set {params}"}

            else:
                response = {"status": "error", "message": "Unknown command"}

        except Exception as e:
            response = {"status": "error", "message": str(e)}

        # 回應給該 client
        try:
            conn.send(json.dumps(response).encode())
        except:
            print(f"⚠ Failed to send response to {addr} (client disconnected)")


    # ----------------------------------------------------
    # 專屬該 client 的接收 thread
    # ----------------------------------------------------
    def recv_loop(self, conn, addr):
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break  # client 斷線

                self.handle_command(data, conn, addr)

        except:
            pass


    # ----------------------------------------------------
    # 專屬該 client 的推資料 thread
    # ----------------------------------------------------
    def push_loop(self, conn, addr):
        global bounding_boxes_json

        while True:
            time.sleep(0.1)

            try:
                conn.send(bounding_boxes_json.encode())
                #print(f"📤 Pushed to {addr}")

            except:
                print(f"⚠ push_loop: {addr} connection lost")
                break   # client 斷線，退出 thread


    # ----------------------------------------------------
    # client handler：控制整個 client 生命周期
    # ----------------------------------------------------
    def client_handler(self, conn, addr):
        print(f"🟢 Handler started for {addr}")

        # 啟動 recv loop
        recv_t = Thread(target=self.recv_loop, args=(conn, addr), daemon=True)
        recv_t.start()

        # 啟動 push loop
        push_t = Thread(target=self.push_loop, args=(conn, addr), daemon=True)
        push_t.start()

        # 等待 recv loop 結束（代表 client 斷線）
        recv_t.join()

        # client handler 收尾
        print(f"⚠ Client disconnected: {addr}")
        conn.close()

        with self.lock:
            if addr in self.clients:
                del self.clients[addr]
            if addr in self.client_threads:
                del self.client_threads[addr]


    # ----------------------------------------------------
    # 伺服器主 loop：等待 client 連線
    # ----------------------------------------------------
    def run(self):
        print("⏳ Waiting for clients...")

        while True:
            conn, addr = self.server_sock.accept()
            print(f"🤝 Client connected: {addr}")

            with self.lock:
                self.clients[addr] = conn

            handler_t = Thread(target=self.client_handler, args=(conn, addr), daemon=True)
            self.client_threads[addr] = handler_t
            handler_t.start()


class FeedforwardGain:
    def __init__(self, gain=200.0, max_output=150.0, alpha=0.3):
        """
        gain        : feedforward gain (Kff)
        max_output  : clamp of final output command
        alpha       : low-pass filter factor (0~1)
        """
        self.gain = gain
        self.max_output = max_output
        self.alpha = alpha

        self.last_position = None
        self.last_time = None
        self._filtered_speed = 0.0

    def calculate_speed(self, position):
        now = time.perf_counter()

        # first frame protection
        if self.last_position is None:
            self.last_position = position
            self.last_time = now
            return 0.0

        # --- dt ---
        dt = now - self.last_time

        # dt clamp (avoid spike)
        dt_min = 0.005
        dt_max = 0.15
        dt = max(dt_min, min(dt, dt_max))

        # --- raw speed ---
        raw_speed = (position - self.last_position) / dt

        # --- low-pass filter ---
        self._filtered_speed = (
            (1.0 - self.alpha) * self._filtered_speed
            + self.alpha * raw_speed
        )

        # update state
        self.last_position = position
        self.last_time = now

        return self._filtered_speed

    def output(self, position):
        speed = self.calculate_speed(position)

        # feedforward output
        output = self.gain * speed

        # clamp final output
        output = max(-self.max_output, min(output, self.max_output))

        return output
        


class Gimbal_Controller:
    def __init__(self,HOST,PORT):
        global lock_xyxy, locked
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #HOST = "192.168.144.64"
        #PORT = 8888
        print(f"Connecting to {HOST}:{PORT} ...")
        self.sock.connect((HOST, PORT))

        self.x_ff_gain = FeedforwardGain(gain=200.0, max_output=150.0, alpha=0.3)
        self.y_ff_gain = FeedforwardGain(gain=200.0, max_output=150.0, alpha=0.3)

        # PID controller params (tunable)
        self.Kp = 400.0
        self.Ki = 0
        self.Kd = 25
        self._int_x = 0.0
        self._int_y = 0.0
        self._prev_x = 0.0
        self._prev_y = 0.0
        self.pid_dt = 0.1            # seconds (match run loop sleep)
        self.output_limit = 128     # clamp to gimbal range

        self.osc_timer = time.time()
        self.osc_last_x = 0
        self.osc_last_y = 0

        

    def set_pid(self, Kp=None, Ki=None, Kd=None, dt=None, output_limit=None):
        """Adjust PID parameters at runtime."""
        if Kp is not None:
            self.Kp = float(Kp)
        if Ki is not None:
            self.Ki = float(Ki)
        if Kd is not None:
            self.Kd = float(Kd)
        if dt is not None:
            self.pid_dt = float(dt)
        if output_limit is not None:
            self.output_limit = int(output_limit)

    def reset_pid(self):
        """Reset integral and derivative state."""
        self._int_x = 0.0
        self._int_y = 0.0
        self._prev_x = 0.0
        self._prev_y = 0.0

    def PID(self, error, axis='x'):
        """
        PID controller.
        - error expected in approx. [-0.5, 0.5]
        - axis: 'x' or 'y' to keep separate state for pan/tilt
        Returns an int command clamped to [-output_limit, output_limit].
        """
        if axis == 'x':
            self._int_x += error * self.pid_dt
            deriv = (error - self._prev_x) / self.pid_dt if self.pid_dt > 0 else 0.0
            self._prev_x = error
            out = self.Kp * error + self.Ki * self._int_x + self.Kd * deriv
        else:
            self._int_y += error * self.pid_dt
            deriv = (error - self._prev_y) / self.pid_dt if self.pid_dt > 0 else 0.0
            self._prev_y = error
            out = self.Kp * error + self.Ki * self._int_y + self.Kd * deriv

        # clamp and return integer
        out = max(-self.output_limit, min(self.output_limit, out))
        return int(out)

    def run(self):
        global lock_xyxy, locked
        while True:
            if not locked:
                time.sleep(0.1)
                continue

            x_ratio = lock_xyxy[0]
            y_ratio = lock_xyxy[1]

            dead_zone = 0.00
            center = 0.5

            x_offset = x_ratio - center
            y_offset = y_ratio - center

            x_gain_value = self.x_ff_gain.output(x_ratio)
            y_gain_value = self.y_ff_gain.output(y_ratio)

            x_pid_value = self.PID(x_offset, axis='x')
            y_pid_value = self.PID(y_offset, axis='y')

            pan = x_pid_value #- x_gain_value  # pan 正向
            tilt = -y_pid_value #+ y_gain_value # tilt 反向
            
            print(f"PID pan: {pan}, tilt: {tilt} | FF pan: {x_gain_value:.1f}, tilt: {y_gain_value:.1f} | PID out pan: {x_pid_value}, tilt: {y_pid_value}")


            if pan != 0 or tilt != 0:
                self.send_command(packet_builder.switch_sport_model())
                self.send_command(packet_builder.do_joystick(pan, tilt))
            else:
                print("🟡 目標在中心，不移動")

            time.sleep(0.1)
    
    def send_command(self,DATA):
        print(f"Sent {len(DATA)} bytes:", DATA.hex(" "))
        self.sock.sendall(DATA)

def ai_gimbal():

    global loop
    global appsrc
    global output_fps
    Gst.init(None)
    
    # load config
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    print("===config===")
    for key, value in config.items():
        print(f"{key}: {value}")
    


    # 1. 建立 2 個gstreamer pipeline 與 1 個AI 推論服務
    
    # input rtsp stream
    rtsp_handler = rtsp_ai_pipline(config["rtsp_src"])
    # ouput udp stream
    udp_stream_handler = udp_pipline(config['udp_sink_ip'],config['udp_sink_port'],output_fps)
    
    # AI result ouput to appsrc
    appsrc = udp_stream_handler.appsrc
    
    # set playing
    rtsp_handler.setStart()
    udp_stream_handler.setStart()
    
    # 接受指令跟縱物件的 server
    ai_control_server = AI_Control_Server(port=config['ai_control_local_port'])
    thread = Thread(target=ai_control_server.run, daemon=True).start()
    
    # 內部控制雲台的 server
    gimbal_controller = Gimbal_Controller(config["gimbal"]["host"],config["gimbal"]["port"])
    thread_gimbal = Thread(target=gimbal_controller.run ,daemon=True).start()
    
    # Gstreamer event loop
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pass


if __name__ == "__main__":
    ai_gimbal()
