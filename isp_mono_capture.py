import argparse
import time
from pathlib import Path
import cv2
import depthai as dai
import numpy as np
from datetime import date

today = str(date.today())
dirName = "images_"+today
def dirsetup():
    Path(dirName).mkdir(parents=True, exist_ok=True)


## arguments
argn = argparse.ArgumentParser()
argn.add_argument('-n', type=int, default=5)      # number of images to collect
argn.add_argument('-iso', type=int, default=400)   # iso of images
argn.add_argument('-fps', type=float, default=1)    # fps of camera
argn.add_argument('-ss', type=float, default=1)   # shutter speed of camera in milliseconds
args = argn.parse_args()


## Create pipeline
pipeline = dai.Pipeline()

# color camera
camRgb = pipeline.create(dai.node.ColorCamera)
camRgb.setBoardSocket(dai.CameraBoardSocket.RGB)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_12_MP)
camRgb.setInterleaved(False)
camRgb.initialControl.setSharpness(0)     # range: 0..4, default: 1		
camRgb.initialControl.setLumaDenoise(0)   # range: 0..4, default: 1		
camRgb.initialControl.setChromaDenoise(4) # range: 0..4, default: 1

# Mono cameras
monoRight = pipeline.create(dai.node.MonoCamera)
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
monoLeft = pipeline.create(dai.node.MonoCamera)
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)

# depth
Depth = pipeline.create(dai.node.StereoDepth)
Depth.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
Depth.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
Depth.setLeftRightCheck(True)
Depth.setExtendedDisparity(False)
Depth.setSubpixel(False)

## Linking
xoutRgb = pipeline.create(dai.node.XLinkOut)
xoutRgb.setStreamName("rgb")
camRgb.isp.link(xoutRgb.input)

xoutRight = pipeline.create(dai.node.XLinkOut)
xoutRight.setStreamName("right")
monoRight.out.link(xoutRight.input)

xoutLeft = pipeline.create(dai.node.XLinkOut)
xoutLeft.setStreamName("left")
monoLeft.out.link(xoutLeft.input)

xoutDepth = pipeline.create(dai.node.XLinkOut)
xoutDepth.setStreamName("disparity")
monoRight.out.link(Depth.right)
monoLeft.out.link(Depth.left)
Depth.disparity.link(xoutDepth.input)

xin = pipeline.create(dai.node.XLinkIn)
xin.setMaxDataSize(1)
xin.setStreamName("control")
xin.out.link(camRgb.inputControl)
# xin.out.link(monoLeft.inputControl)
# xin.out.link(monoRight.inputControl)


def set_ss_iso(expTimeMs, sensIso):
    expTimeUs = int(round(expTimeMs * 1000))
    ctrl = dai.CameraControl()
    ctrl.setManualExposure(expTimeUs, sensIso)
    qControl.send(ctrl)


def set_fps(fps):
    camRgb.setFps(fps)
    monoRight.setFps(fps)
    monoLeft.setFps(fps)


# Connect to device and start pipeline
with dai.Device(pipeline) as device:	
    n = args.n      # image count
    dirsetup()
    init_dsp = (255 / Depth.initialConfig.getMaxDisparity())

    qRight = device.getOutputQueue(name="right", maxSize=2, blocking=False)
    qLeft = device.getOutputQueue(name="left", maxSize=2, blocking=False)
    qRGB = device.getOutputQueue(name="rgb", maxSize=2, blocking=False)
    qDepth = device.getOutputQueue(name="disparity", maxSize=2, blocking=False)
    qControl = device.getInputQueue(name="control")

    # iso and shutter speed
    set_ss_iso(args.ss, args.iso)
    # fps
    set_fps(args.fps)

    for r in range(30):
        c, r, l, d = qRGB.get(), qRight.get(), qLeft.get(), qDepth.get()

    print("Started")
    start = time.time()

    i = 0
    while(i<n):
        t = str(time.time())

        inRgb = qRGB.tryGet()
        inRight = qRight.tryGet()
        inLeft = qLeft.tryGet()
        inDepth = qDepth.tryGet()
        if inRgb is not None:
            cv2.imwrite(f"{dirName}/{t}_Rgb.png", inRgb.getCvFrame())
        if inRight is not None:
            cv2.imwrite(f"{dirName}/{t}_Right.png", inRight.getFrame())
        if inLeft is not None:
            cv2.imwrite(f"{dirName}/{t}_Left.png", inLeft.getFrame())
        if inDepth is not None:
            dframe = inDepth.getFrame()
            dframe = (dframe * init_dsp).astype(np.uint8)
            cv2.imwrite(f"{dirName}/{t}_Depth.png", dframe)
        
        i += 1

print("Finished in", round(time.time()-start, 2))
