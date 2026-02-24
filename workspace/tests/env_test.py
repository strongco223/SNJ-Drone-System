import subprocess
import torch
import sys

def check_gstreamer_gpu():
    print("🔍 Checking GStreamer GPU-related plugins...\n")
    try:
        # 列出所有 GStreamer plugin
        result = subprocess.run(["gst-inspect-1.0"], capture_output=True, text=True)
        plugins = result.stdout

        gpu_plugins = [
            "nvvidconv", "nvarguscamerasrc", "nvv4l2h264enc",
            "nvv4l2decoder", "nvvideoconvert", "nvjpegdec"
        ]

        found = [p for p in gpu_plugins if p in plugins]
        missing = [p for p in gpu_plugins if p not in plugins]

        if found:
            print(f"✅ Found GPU-accelerated GStreamer plugins: {', '.join(found)}")
        else:
            print("⚠️ No NVIDIA GStreamer GPU plugins found.")

        if missing:
            print(f"⚠️ Missing plugins: {', '.join(missing)}")

        # 驗證 GStreamer 是否可使用 CUDA context
        test_cmd = [
            "gst-launch-1.0", "-v",
            "videotestsrc", "num-buffers=1",
            "!", "nvvideoconvert", "!", "fakesink"
        ]
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GStreamer pipeline with nv plugins executed successfully.\n")
        else:
            print("❌ GStreamer pipeline failed.\n")
            print(result.stderr)
    except FileNotFoundError:
        print("❌ GStreamer is not installed or gst-launch-1.0 not found.\n")

def check_yolov11_gpu():
    print("🔍 Checking YOLOv11 GPU support...\n")
    try:
        import ultralytics
        model = ultralytics.YOLO('yolov11n.pt')
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🧠 PyTorch CUDA available: {torch.cuda.is_available()}")
        print(f"🚀 Current device: {device}")

        if torch.cuda.is_available():
            try:
                model.to('cuda')
                print("✅ YOLOv11 model successfully moved to GPU.")
            except Exception as e:
                print(f"⚠️ YOLOv11 failed to use GPU: {e}")
        else:
            print("⚠️ CUDA not detected — YOLOv11 running on CPU.")

    except ImportError as e:
        print(f"❌ YOLOv11 (ultralytics) not installed: {e}")
    except Exception as e:
        print(f"⚠️ YOLOv11 test failed: {e}")

def main():
    print("=" * 60)
    print("🧪 GPU Capability Check for Jetson: GStreamer + YOLOv11")
    print("=" * 60, "\n")

    check_gstreamer_gpu()
    print("-" * 60)
    check_yolov11_gpu()
    print("\n✅ Done.")

if __name__ == "__main__":
    main()
