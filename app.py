from flask import Flask, render_template, Response, request, redirect
import cv2
import datetime, time
import os, sys
import numpy as np
from threading import Thread
# ------------------------------------------------------------
import mediapipe as mp
import math

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands                       #MediaPipe
from handpose import vector_2d_angle, hand_angle, hand_pos
#-----------------------------------------------------------
import subprocess
current_directory = os.path.dirname(os.path.abspath(__file__))
detect_path = os.path.join(current_directory, '../yolov7')
sys.path.append(detect_path)
#--------------------------------------------------------json
import json
from json import load
#--------------------------------------------------------
import pymongo
ConnectionString =  "mongodb://localhost:27017"



global switch
switch=0

#make shots directory to save pics
try:
    os.mkdir('./shots')
except OSError as error:
    pass

#instatiate flask app  
app = Flask(__name__, template_folder='./templates')

camera = cv2.VideoCapture(0)

def gen_frames():  # generate frame by frame from camera
    global out, capture,rec_frame
    while True:
        success, frame = camera.read() 
        if success:             
            try:
                ret, buffer = cv2.imencode('.jpg', cv2.flip(frame,1))
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                pass
                
        else:
            pass
#------------------------------------------------------------------------------------------------------
fontFace = cv2.FONT_HERSHEY_SIMPLEX  # 印出文字的字型
lineType = cv2.LINE_AA               # 印出文字的邊框


@app.route('/')
def index():
    return render_template('index.html')   


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/requests',methods=['POST','GET'])
def tasks():
    
    global switch,camera
    if request.method == 'POST':
        if request.form.get('stop') == 'Stop/Start':
            if(switch==1):                            #當stop的時候
                switch=0
                camera.release()
                cv2.destroyAllWindows()                
            else:                                     #當start的時候
                #啟動相機 
                CountDonw=5
                camera = cv2.VideoCapture(0)               
                with mp_hands.Hands(
                    model_complexity=0,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5) as hands:
                    #如果沒有偵測到相機
                    if not camera.isOpened():         
                        print("Cannot open camera")
                        exit()
                    # 影像尺寸
                    w, h = 300, 300  
                    #現階段儲存                               
                    
                    while True:
                        ret, img = camera.read()
                        img = cv2.flip(img,1)
                        # 縮小尺寸，加快處理效率
                        img = cv2.resize(img, (w,h))                 
                        if not ret:
                            print("Cannot receive frame")
                            break
                        img2 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # 轉換成 RGB 色彩
                        results = hands.process(img2)                # 偵測手勢
                        if results.multi_hand_landmarks:
                            for hand_landmarks in results.multi_hand_landmarks:
                                finger_points = []                   # 記錄手指節點座標的串列
                            for i in hand_landmarks.landmark:
                                # 將 21 個節點換算成座標，記錄到 finger_points
                                x = i.x*w
                                y = i.y*h
                                finger_points.append((x,y))
                            
                            if finger_points:
                                finger_angle = hand_angle(finger_points) # 計算手指角度，回傳長度為 5 的串列
                                #print(finger_angle)                     # 印出角度 ( 有需要就開啟註解 )
                                text = hand_pos(finger_angle)            # 取得手勢所回傳的內容
                                if CountDonw > 0 & CountDonw <=5:
                                    print(CountDonw)
                                    CountDonw = CountDonw-1
                                else:
                                    now = datetime.datetime.now()              
                                    
                                    # p = os.path.sep.join(['shots', "shot_{}.png".format(str(now).replace(":",''))])
                                    p = os.path.sep.join(['shots', "shot_01.png"])
                                    cv2.imwrite(p, img)
                                    jsonFile = open("../FianlProject/update.json","w")
                                    
                                    data={
                                        "state":text,
                                        "time":str(now.strftime('%Y/%m/%d %H:%M:%S'))
                                    }
                                    json.dump(data, jsonFile)
                                    return redirect('http://127.0.0.1:5000/detect')
                                    
                                time.sleep(1)
                                cv2.putText(img2, text, (30,120), fontFace, 5, (255,255,255), 10, lineType) # 印出文字
                                print(text)
                        else:
                            CountDonw = 5

    elif request.method=='GET':
        return render_template('index.html')
    return render_template('index.html')

@app.route('/detect',methods=['POST','GET'])
def detect():
    cmd_command = "cd.. && cd FianlProject && cd yolov7 && python detect.py"
    subprocess.run(cmd_command, shell=True, stdout=subprocess.PIPE, text=True)
    
    #連線位置
    client = pymongo.MongoClient(ConnectionString)
    #資料庫名稱
    db = client['Crow']
    #讀取資料json
    jsonFile = open("./update.json","r")
    a = json.load(jsonFile)
    #資料表名稱
    collection = db.sensorLog
    #格式
    data={
        "state":a['state'],
        "time":a['time'],
        "staff":a['staff']
    }
    #插入  
    sensor_id =collection.insert_one(data).inserted_id
    print (f"id:{sensor_id}has been created")

    
    return render_template('home.html',state=a['state'],time=a['time'],staff=a['staff'])


@app.route('/log',methods=['POST','GET'])
def log():
    client = pymongo.MongoClient(ConnectionString)
    #資料庫名稱
    db = client['Crow']
    #資料表名稱
    collection = db.sensorLog
    data=collection.find()
    print(data)   
    
    return render_template('log.html',datas = data)  


if __name__ == '__main__':
    app.debug = True #開啟DEBUG模式 
    app.run()
    
camera.release()
cv2.destroyAllWindows()     