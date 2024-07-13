# Ultralytics YOLO 🚀, AGPL-3.0 license

import cv2
import pytest

from ultralytics import YOLO, solutions
from ultralytics.utils.downloads import safe_download

MAJOR_SOLUTIONS_DEMO = "https://github.com/ultralytics/assets/releases/download/v0.0.0/solutions_ci_demo.mp4"
WORKOUTS_SOLUTION_DEMO = "https://github.com/ultralytics/assets/releases/download/v0.0.0/solutions_ci_pose_demo.mp4"


@pytest.mark.slow
def test_major_solutions():
    """Test the object counting, heatmap, speed estimation and queue management solution."""

    safe_download(url=MAJOR_SOLUTIONS_DEMO)
    model = YOLO("yolov8n.pt")
    names = model.names
    cap = cv2.VideoCapture("solutions_ci_demo.mp4")
    assert cap.isOpened(), "Error reading video file"

    region_points = [(20, 400), (1080, 404), (1080, 360), (20, 360)]

    counter = solutions.ObjectCounter(reg_pts=region_points, classes_names=names, view_img=False)
    heatmap = solutions.Heatmap(colormap=cv2.COLORMAP_PARULA, classes_names=names, view_img=False)
    speed = solutions.SpeedEstimator(reg_pts=region_points, names=names, view_img=False)
    queue = solutions.QueueManager(classes_names=names, reg_pts=region_points, view_img=False)

    while cap.isOpened():
        success, im0 = cap.read()
        if not success:
            break
        original_im0 = im0.copy()
        tracks = model.track(im0, persist=True, show=False)
        im0_counting = counter.start_counting(original_im0.copy(), tracks)
        im0_heatmap = heatmap.generate_heatmap(original_im0.copy(), tracks)
        im0_speed = speed.estimate_speed(original_im0.copy(), tracks)
        im0_queue = queue.process_queue(original_im0.copy(), tracks)

    cap.release()
    cv2.destroyAllWindows()


@pytest.mark.slow
def test_aigym():
    """Test the workouts monitoring solution."""

    safe_download(url="")
    model = YOLO("yolov8n-pose.pt")
    cap = cv2.VideoCapture("solutions_ci_pose_demo.mp4")
    assert cap.isOpened(), "Error reading video file"

    gym_object = solutions.AIGym(line_thickness=2, pose_type="squat", kpts_to_check=[5, 11, 13])
    while cap.isOpened():
        success, im0 = cap.read()
        if not success:
            break
        results = model.track(im0, verbose=False)
        im0 = gym_object.start_counting(im0, results)
    cap.release()
    cv2.destroyAllWindows()
