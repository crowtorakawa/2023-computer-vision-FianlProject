from flask import Flask, render_template, Response, request, redirect
import cv2
import datetime, time
import os, sys
import numpy as np
import json
import subprocess
import pymongo

# handpose 模組 (請確定 handpose.py 在同一資料夾或在 sys.path)
from handpose import vector_2d_angle, hand_angle, hand_pos

# mediapipe
import mediapipe as mp
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

# --------------------------------------------
current_directory = os.path.dirname(os.path.abspath(__file__))
shots_dir = os.path.join(current_directory, 'shots')
os.makedirs(shots_dir, exist_ok=True)

# yolov7 directory (相對於 app.py)
yolov7_dir = os.path.join(current_directory, 'yolov7')  # 如果 yolov7 在同目錄下的 yolov7 資料夾
update_json_path = os.path.join(current_directory, 'update.json')

# MongoDB 連線字串
ConnectionString = "mongodb://localhost:27017"

# camera global
camera = cv2.VideoCapture(0)
switch = 0

app = Flask(__name__, template_folder='./templates')

def gen_frames():  # generate frame by frame from camera
    global camera
    while True:
        if camera is None or not camera.isOpened():
            time.sleep(0.1)
            continue
        success, frame = camera.read()
        if not success:
            time.sleep(0.01)
            continue
        try:
            ret, buffer = cv2.imencode('.jpg', cv2.flip(frame, 1))
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print("gen_frames error:", e)
            time.sleep(0.01)
            continue

# OpenCV print text config
fontFace = cv2.FONT_HERSHEY_SIMPLEX
lineType = cv2.LINE_AA

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/requests', methods=['POST', 'GET'])
def tasks():
    global switch, camera
    if request.method == 'POST':
        if request.form.get('stop') == 'Stop/Start':
            if switch == 1:
                switch = 0
                if camera and camera.isOpened():
                    camera.release()
                cv2.destroyAllWindows()
            else:
                # start camera & run detection until a gesture triggers redirect
                switch = 1
                countdown = 5
                camera = cv2.VideoCapture(0)

                if not camera.isOpened():
                    print("Cannot open camera")
                    return render_template('index.html', error="Cannot open camera")

                # 固定推定大小 (注意: x = lm.x * width)
                width, height = 300, 300

                with mp_hands.Hands(
                    model_complexity=0,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5) as hands:

                    while True:
                        ret, img = camera.read()
                        if not ret:
                            print("Cannot receive frame")
                            break

                        img = cv2.flip(img, 1)
                        img_resized = cv2.resize(img, (width, height))
                        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
                        results = hands.process(img_rgb)

                        if results.multi_hand_landmarks:
                            # 針對每隻手做處理
                            for hand_landmarks in results.multi_hand_landmarks:
                                finger_points = []
                                for lm in hand_landmarks.landmark:
                                    x = int(lm.x * width)
                                    y = int(lm.y * height)
                                    finger_points.append((x, y))

                                if finger_points:
                                    try:
                                        finger_angle = hand_angle(finger_points)
                                        text = hand_pos(finger_angle)
                                    except Exception as e:
                                        print("handpose error:", e)
                                        text = ""

                                    # countdown 機制：先顯示倒數，倒數完再拍照
                                    if 0 < countdown <= 5:
                                        print("countdown:", countdown)
                                        countdown -= 1
                                        time.sleep(1)
                                    else:
                                        now = datetime.datetime.now()
                                        filename = f"shot_{now.strftime('%Y%m%d_%H%M%S')}.png"
                                        p = os.path.join(shots_dir, filename)
                                        # 儲存原始大小（非 resized），或存 resized 視需求
                                        cv2.imwrite(p, img)

                                        # 寫入 update.json (包含 staff 欄位預設為空字串)
                                        data = {
                                            "state": text,
                                            "time": now.strftime('%Y/%m/%d %H:%M:%S'),
                                            "staff": ""   # 若你有 staff 資訊，這裡放入
                                        }
                                        try:
                                            with open(update_json_path, "w", encoding='utf-8') as jf:
                                                json.dump(data, jf, ensure_ascii=False)
                                        except Exception as e:
                                            print("write update.json error:", e)

                                        # 偵測到手勢並儲存後，跳到 /detect 去執行 yolov7
                                        return redirect('/detect')

                                    # 在畫面上顯示偵測到的文字（debug）
                                    cv2.putText(img_resized, text, (10, 40), fontFace, 1, (255, 255, 255), 2, lineType)
                        else:
                            countdown = 5

                # 關閉 camera（若 while 退出）
                if camera and camera.isOpened():
                    camera.release()
                    cv2.destroyAllWindows()

    elif request.method == 'GET':
        return render_template('index.html')
    return render_template('index.html')

@app.route('/detect', methods=['POST', 'GET'])
def detect():
    # 執行 yolov7 detect.py（以 yolov7_dir 為 working dir）
    try:
        if not os.path.isdir(yolov7_dir):
            print("yolov7 directory not found:", yolov7_dir)
        else:
            subprocess.run(['python', 'detect.py'], cwd=yolov7_dir, stdout=subprocess.PIPE, text=True)
    except Exception as e:
        print("subprocess error:", e)

    # 連線 MongoDB
    client = pymongo.MongoClient(ConnectionString)
    db = client['Crow']

    # 讀取 update.json
    try:
        with open(update_json_path, "r", encoding='utf-8') as jf:
            a = json.load(jf)
    except Exception as e:
        print("read update.json error:", e)
        a = {"state": "", "time": "", "staff": ""}

    collection = db.sensorLog
    data = {
        "state": a.get('state', ''),
        "time": a.get('time', ''),
        "staff": a.get('staff', '')
    }

    try:
        sensor_id = collection.insert_one(data).inserted_id
        print(f"id:{sensor_id} has been created")
    except Exception as e:
        print("mongodb insert error:", e)

    return render_template('home.html', state=a.get('state', ''), time=a.get('time', ''), staff=a.get('staff', ''))

@app.route('/log', methods=['POST', 'GET'])
def log():
    client = pymongo.MongoClient(ConnectionString)
    db = client['Crow']
    collection = db.sensorLog
    try:
        data_cursor = collection.find().sort([('_id', -1)])
        data_list = list(data_cursor)
    except Exception as e:
        print("mongodb find error:", e)
        data_list = []

        
    return render_template('log.html', datas=data_list)

if __name__ == '__main__':
    # 用 try/finally 確保 camera 在結束時釋放
    try:
        app.debug = True
        app.run()
    finally:
        if camera and camera.isOpened():
            camera.release()
        cv2.destroyAllWindows()
