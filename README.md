[![Ultralytics CI](https://github.com/ultralytics/ultralytics/actions/workflows/ci.yaml/badge.svg)](https://github.com/ultralytics/ultralytics/actions/workflows/ci.yaml)

## Install

```bash
pip install ultralytics
```
Development
```
git clone https://github.com/ultralytics/ultralytics
cd ultralytics
pip install -e .
```

## Usage
### 1. CLI
To simply use the latest Ultralytics YOLO models
```bash
yolo task=detect    mode=train  model=s.yaml ...
          classify       infer        s-cls.yaml
          segment        val          s-seg.yaml
```
### 2. Python SDK
To use pythonic interface of Ultralytics YOLO model
```python
import ultralytics
from ultralytics import YOLO

model = YOLO()
model.new("s-seg.yaml") # automatically detects task type
model.load("s-seg.pt") # load checkpoint
model.train(data="coco128-segments", epochs=1, lr0=0.01, ...)
```
If you're looking to modify YOLO for R&D or to build on top of it, refer to [Using Trainer]() Guide on our docs.


## Models


| Model                                                                                            | size<br><sup>(pixels) | mAP<sup>val<br>50-95 | Speed<br><sup>CPU<br>(ms) | Speed<br><sup>T4 GPU<br>(ms) | params<br><sup>(M) | FLOPs<br><sup>(B) |
|--------------------------------------------------------------------------------------------------|-----------------------|----------------------|---------------------------|------------------------------|--------------------|-------------------|
| [YOLOv5n](https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5n.pt)               | 640                   | 28.0                 | -                         | -                            | **1.9**            | **4.5**           |
| [YOLOv6n](url)                                                                                   | 640                   | 35.9                 | -                         | -                            | 4.3                | 11.1              |
| **[YOLOv8n](url)**                                                                               | 640                   | -                    | -                         | -                            | 2.3                | 9.5               |
|                                                                                                  |                       |                      |                           |                              |                    |                   |                        |
| [YOLOv5s](https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5s.pt)               | 640                   | 37.4                 | -                         | -                            | 7.2                | 16.5              |
| [YOLOv6s](url)                                                                                   | 640                   | 43.5                 | -                         | -                            | 17.2               | 44.2              |
| **[YOLOv8s](url)**                                                                               | 640                   | -                    | -                         | -                            | 6.6                | 24.6              |
|                                                                                                  |                       |                      |                           |                              |                    |                   |
| [YOLOv5m](https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5m.pt)               | 640                   | 45.4                 | -                         | -                            | 21.2               | 49.0              |
| [YOLOv6m](url)                                                                                   | 640                   | 49.5                 | -                         | -                            | 34.3               | 82.2              |
| **[YOLOv8m](url)**                                                                               | 640                   | -                    | -                         | -                            | 19.6               | 73.4              |
|                                                                                                  |                       |                      |                           |                              |                    |                   |
| [YOLOv5l](https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5l.pt)               | 640                   | 49.0                 | -                         | -                            | 46.5               | 109.1             |
| [YOLOv6l](url)                                                                                   | 640                   | 52.5                 | -                         | -                            | 58.5               | 144.0             |
| [YOLOv7](url)                                                                                    | 640                   | 51.2                 | -                         | -                            | 36.9               | 104.7             |
| **[YOLOv8l](url)**                                                                               | 640                   | **52.9**             | -                         | -                            | 43.7               | 165.7             |
|                                                                                                  |                       |                      |                           |                              |                    |                   |
| [YOLOv5x](https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5x.pt)               | 640                   | 50.7                 | -                         | -                            | 86.7               | 205.7             |
| [YOLOv7-X](url)                                                                                  | 640                   | 52.9                 | -                         | -                            | 71.3               | 189.9             |
| **[YOLOv8x](url)**                                                                               | 640                   | **53.8**             | -                         | -                            | 68.2               | 258.5             |
|                                                                                                  |                       |                      |                           |                              |                    |                   |
| [YOLOv5x6](https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5x6.pt)             | 1280                  | 55.0                 | -                         | -                            | 140.7              | 839.2             |
| [YOLOv7-E6E](url)                                                                                | 1280                  | 56.8                 | -                         | -                            | 151.7              | 843.2             |
| **[YOLOv8x6](https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5x6.pt)**<br>+TTA | 1280                  | -<br>-               | -<br>-                    | -<br>-                       | 97.4               | 1047.2<br>-       |
