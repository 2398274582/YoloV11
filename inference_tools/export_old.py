from ultralytics import YOLO
# For more info visit: # https://docs.ultralytics.com/modes/export/
print(" 🚀 Exporting model .......")
# Load model
model = YOLO('/home/johnny/Projects/models/detector_best.pt', task='detect')

# Export to ONNX, the model is saved next to original with .onnx extension
model.export(
    format='onnx',  # destination format
    imgsz=640,  # inference size (pixels)
    half=False,  # use FP16 half-precision inference
    dynamic=False,  # ONNX export only supports static size
    simplify=False,  # ONNX export only supports static size
    opset=11,  # ONNX opset version
)
