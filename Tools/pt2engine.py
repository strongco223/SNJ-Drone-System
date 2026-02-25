import sys
from ultralytics import YOLO


def pt_to_trt(pt_path: str, img_w: int, img_h: int):
    model = YOLO(pt_path)

    model.export(
        format="engine",
        imgsz=(img_h, img_w),  # Ultralytics 使用 (H, W)
        half=False,            # FP32
        device=0,
        project="output",
        name="trt_model"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python pt2tensorRT.py <input_path> <img_w> <img_h>")
        sys.exit(1)

    input_path = sys.argv[1]
    img_w = int(sys.argv[2])
    img_h = int(sys.argv[3])

    pt_to_trt(input_path, img_w, img_h)

    # example usage:
    # python pt2engine.py ../workspace/yolo11n.pt 960 540 