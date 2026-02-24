gst-launch-1.0 \
rtspsrc location=rtsp://192.168.144.64:554/H264 latency=50 ! \
rtph264depay ! h264parse ! avdec_h264 ! \
videoconvert ! autovideosink
