# -*- coding: utf-8 -*-
import cv2
import numpy as np
import pyautogui
import time
import smtplib
import tkinter as tk
import ctypes
import os
import random
import requests
import threading
import re  # 이메일 유효성 검사용 정규표현식 라이브러리
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# PyTorch 및 인공신경망 라이브러리
import torch
import torch.nn as nn

try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("⚠️ pywin32 라이브러리가 없어 pyautogui 방식으로 대체합니다.")

# Windows 디스플레이 DPI 확대 배율 비활성화
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

# ─────────────────────────────────────────
# 자격 증명 데이터 (Base64 인코딩)
# ─────────────────────────────────────────
from config import *

# ─────────────────────────────────────────
# 제어 변수 설정
# ─────────────────────────────────────────
DIFF_THRESHOLD       = 25
SATURATION_THRESHOLD = 30
CHANGE_MIN_PIXELS    = 5
REFRESH_INTERVAL     = 3.0
PAGE_LOAD_WAIT       = 2.5
COOLDOWN_AFTER_ALERT = 15
MODEL_DISTANCE_THRESHOLD = 0.5

IS_RUNNING = True
stop_btn_root = None

class SiameseNetwork(nn.Module):
    def __init__(self):
        super(SiameseNetwork, self).__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Flatten()
        )
        self.fc = nn.Linear(64 * 8 * 8, 16)

    def forward_once(self, x):
        return self.fc(self.cnn(x))

    def forward(self, input1, input2):
        output1 = self.forward_once(input1)
        output2 = self.forward_once(input2)
        return output1, output2

def load_deeplearning_model():
    if getattr(sys, 'frozen', False):
        current_dir = sys._MEIPASS
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))

    paths_to_try = [
        os.path.join(current_dir, "siamese_ticket_model.pth")
    ]
    model_path = None
    for p in paths_to_try:
        if os.path.exists(p):
            model_path = p
            break

    print("\n" + "="*60, flush=True)
    print("[분석 알고리즘 가동 검사]", flush=True)
    print("="*60, flush=True)

    if model_path:
        try:
            model = SiameseNetwork()
            model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            model.eval()
            print("성공: 샴 네트워크 가중치 로드 완료! 스마트 판독 개시.", flush=True)
            return model
        except Exception as e:
            print(f"에러: 가중치 로드 실패: {e}", flush=True)
            return None
    else:
        print("경고: 가중치 파일을 찾을 수 없습니다. 기본 분석으로 전환합니다.", flush=True)
        return None

#마우스 움직임 제어(사람 모방)
def human_move_and_click(target_x, target_y):
    if not WIN32_AVAILABLE:
        pyautogui.moveTo(target_x, target_y, duration=random.uniform(0.14, 0.22), tween=pyautogui.easeInOutSine)
        pyautogui.click()
        return

    start_x, start_y = win32api.GetCursorPos()

    distance = np.hypot(target_x - start_x, target_y - start_y)
    if distance > 2:
        control_scale = random.uniform(0.1, 0.3)
        ctrl_x1 = start_x + (target_x - start_x) * control_scale + random.randint(-30, 30)
        ctrl_y1 = start_y + (target_y - start_y) * control_scale + random.randint(-30, 30)
        ctrl_x2 = start_x + (target_x - start_x) * (1.0 - control_scale) + random.randint(-30, 30)
        ctrl_y2 = start_y + (target_y - start_y) * (1.0 - control_scale) + random.randint(-30, 30)

        steps = int(max(6, min(20, distance / 25)))
        for i in range(1, steps + 1):
            t = i / float(steps)
            t_smooth = -(np.cos(np.pi * t) - 1) / 2.0
            inv_t = 1.0 - t_smooth
            x = (inv_t**3 * start_x + 3 * inv_t**2 * t_smooth * ctrl_x1 + 3 * inv_t * t_smooth**2 * ctrl_x2 + t_smooth**3 * target_x)
            y = (inv_t**3 * start_y + 3 * inv_t**2 * t_smooth * ctrl_y1 + 3 * win32api.GetCursorPos()[1] + t_smooth**3 * target_y) # 원본 베지에 형태 유지
            x = (inv_t**3 * start_x + 3 * inv_t**2 * t_smooth * ctrl_x1 + 3 * inv_t * t_smooth**2 * ctrl_x2 + t_smooth**3 * target_x)
            y = (inv_t**3 * start_y + 3 * inv_t**2 * t_smooth * ctrl_y1 + 3 * inv_t * t_smooth**2 * ctrl_x2 + t_smooth**3 * target_y)
            win32api.SetCursorPos((int(x + random.randint(-1, 1)), int(y + random.randint(-1, 1))))
            time.sleep(random.uniform(0.003, 0.008))

    win32api.SetCursorPos((target_x, target_y))
    time.sleep(random.uniform(0.04, 0.08))

    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
    time.sleep(random.uniform(0.06, 0.13))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
    time.sleep(random.uniform(0.02, 0.05))

def click_refresh_region(x1, y1, x2, y2):
    padding_x = int((x2 - x1) * 0.15) + 1
    padding_y = int((y2 - y1) * 0.15) + 1
    rx = random.randint(x1 + padding_x, x2 - padding_x)
    ry = random.randint(y1 + padding_y, y2 - padding_y)
    time.sleep(random.uniform(0.1, 0.3))
    human_move_and_click(rx, ry)
    print(f" 새로고침 랜덤 클릭 ({rx}, {ry})          ", end='\r', flush=True)

def capture_region(x1, y1, x2, y2):
    return cv2.cvtColor(np.array(pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))), cv2.COLOR_RGB2BGR)

def detect_popup_simple(before_gray, after_gray):
    h, w = before_gray.shape
    darkening = float(np.mean(before_gray)) - float(np.mean(after_gray))

    x1, x2 = int(w * 0.15), int(w * 0.85)
    y1, y2 = int(h * 0.10), int(h * 0.70)
    roi_before = before_gray[y1:y2, x1:x2]
    roi_after = after_gray[y1:y2, x1:x2]

    roi_diff = cv2.absdiff(roi_before, roi_after)
    _, roi_bin = cv2.threshold(roi_diff, 25, 255, cv2.THRESH_BINARY)
    roi_change_ratio = float(np.count_nonzero(roi_bin)) / roi_bin.size

    bright_thresh = 210
    bright_ratio_gain = float(np.mean(roi_after > bright_thresh)) - float(np.mean(before_gray > bright_thresh))

    dark_thresh = 80
    dark_ratio_gain = float(np.mean(roi_after < dark_thresh)) - float(np.mean(before_gray < dark_thresh))

    contours, _ = cv2.findContours(roi_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rect_found = False
    max_rect_ratio = 0.0
    for cnt in contours:
        if cv2.contourArea(cnt) < 400: continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        rect_ratio = (cw * ch) / float(roi_bin.size)
        aspect = cw / float(max(ch, 1))
        if 0.8 <= aspect <= 5.5:
            rect_found = True
            max_rect_ratio = max(max_rect_ratio, rect_ratio)

    strong_rect = rect_found and max_rect_ratio > 0.05
    strong_bright = bright_ratio_gain > 0.05
    strong_dark = dark_ratio_gain > 0.04

    #팝업 판단 기준
    print("\n" + "="*50, flush=True)
    print("[알고리즘 팝업 판독 스냅샷 수치]", flush=True)
    print(f" 1. ROI 변화율(영역 변경): {roi_change_ratio:.4f} (성공전환 기준: > 0.85면 0점 처리)", flush=True)
    print(f" 2. 전체 명암 변화량(암전): {darkening:.2f}", flush=True)
    print(f" 3. 흰색 영역 증가량: {bright_ratio_gain:.4f} (합격 기준: > 0.05)", flush=True)
    print(f" 4. 검은 영역 증가량: {dark_ratio_gain:.4f} (합격 기준: > 0.04)", flush=True)
    print(f" 5. 검출 사각형 면적 비율: {max_rect_ratio:.4f} (합격 기준: > 0.05)", flush=True)
    print(f" 6. 최종 조건 매칭 상태 -> 사각형:{strong_rect} | 밝은박스:{strong_bright} | 어두운박스:{strong_dark}", flush=True)
    print("=" * 50, flush=True)

    # [결제창 진입 예외 방어 조건 추가]
    # 화면이 전체적으로 크게 밝아지면서(darkening < -15) 흰색 영역이 대폭 증가(bright_ratio_gain > 0.20)했다면,
    # 이는 팝업이 아니라 티켓팅사이트의 '하얀색 결제/단계 진입 창'으로 정상 이동.
    if darkening < -15 and bright_ratio_gain > 0.20:
        print("[조기 탈락] 사유: 화면 전체 복사형 백색 전환 감지 (정상 결제선 진입으로 판단).", flush=True)
        return False, 0.0

    if roi_change_ratio > 0.85 and not strong_dark:
        print("[조기 탈락] 사유: 전체 화면이 백색으로 전환되는 성공 페이지 이동으로 간주함.", flush=True)
        return False, 0.0

    if not (strong_rect or strong_bright or strong_dark):
        print("[조기 탈락] 사유: 팝업 다운 결정적 특징이 하나도 발견되지 않음.", flush=True)
        return False, 0.0

    score = 0.0
    if strong_rect: score += 0.9
    if strong_bright: score += 0.9
    if strong_dark: score += 0.9
    if darkening > 8: score += 0.3
    if roi_change_ratio > 0.10: score += 0.2

    print(f"[판독 완료] 최종 점수 계산 결과: {score:.1f}", flush=True)
    return score >= 1.4, score

def send_notification_email(target_email, subject, body_html, viz_bytes=None):
    try:
        msg_outer = MIMEMultipart('related')
        msg_outer['From'] = SENDER_EMAIL
        msg_outer['To'] = target_email
        msg_outer['Subject'] = "=?utf-8?b?" + base64.b64encode(subject.encode('utf-8')).decode() + "?="

        msg_alternative = MIMEMultipart('alternative')
        msg_outer.attach(msg_alternative)
        msg_html = MIMEText(body_html, 'html', 'utf-8')
        msg_alternative.attach(msg_html)

        if viz_bytes:
            img_part = MIMEImage(viz_bytes, _subtype='png')
            img_part.add_header('Content-ID', '<viz_img>')
            img_part.add_header('Content-Disposition', 'inline', filename='viz_img.png')
            msg_outer.attach(img_part)

        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, target_email, msg_outer.as_string())
        server.quit()
        print(f"[이메일 알림 발송 완료]", flush=True)
    except Exception as e:
        print(f"[메일 실패] {e}", flush=True)

def send_telegram_alert(chat_id, message, img_bytes=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        if img_bytes:
            files = {'photo': ('alert.png', img_bytes, 'image/png')}
            data = {'chat_id': str(chat_id), 'caption': message}
            requests.post(url, files=files, data=data)
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={'chat_id': chat_id, 'text': message})
        print(f"[텔레그램 스마트폰 푸시 전송 완료]", flush=True)
    except Exception as e:
        print(f"[텔레그램 전송 예외 발생] {e}", flush=True)

def auto_detect_chat_id():
    secret_code = str(random.randint(1000, 9999))
    print("\n" + "="*50, flush=True)
    print("[보안 인증] 스마트폰 텔레그램 연동", flush=True)
    print(f"텔레그램 앱에서 [@hhkalimi_bot] 방에 인증번호 [ {secret_code} ]를 보내주세요.\n", flush=True)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    last_update_id = 0
    while True:
        try:
            resp = requests.get(url).json()
            if resp.get("ok") and resp["result"]:
                for item in resp["result"]:
                    if item["update_id"] > last_update_id:
                        last_update_id = item["update_id"]
                        if item.get("message", {}).get("text", "") == secret_code:
                            print("연동 성공!\n", flush=True)
                            return str(item["message"]["chat"]["id"])
        except: pass
        time.sleep(1.5)

def analyze_changes(prev_gray, curr_gray, prev_frame, curr_frame):
    diff = cv2.absdiff(prev_gray, curr_gray)
    _, diff_thresh = cv2.threshold(diff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    hsv = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2HSV)
    _, sat_mask = cv2.threshold(hsv[:, :, 1], SATURATION_THRESHOLD, 255, cv2.THRESH_BINARY)
    final_mask = cv2.bitwise_and(diff_thresh, sat_mask)
    changed_px = np.count_nonzero(final_mask)

    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    viz_img = curr_frame.copy()
    regions = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 2 or h < 2 or w > 25 or h > 25: continue
        regions.append((x, y, w, h))
        cv2.rectangle(viz_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    changed_rows = sorted(list(set([(y // 15) + 1 for (x, y, w, h) in regions])))
    _, buf = cv2.imencode('.png', viz_img)
    viz_bytes = buf.tobytes()

    return changed_px, regions, changed_rows, viz_bytes

def monitor_loop(wx1, wy1, wx2, wy2, rx1, ry1, rx2, ry2, nx1, ny1, nx2, ny2, box_area, choice, chat_id, user_email, model_backend):
    global IS_RUNNING, stop_btn_root

    click_refresh_region(rx1, ry1, rx2, ry2)
    time.sleep(PAGE_LOAD_WAIT)
    prev_frame = capture_region(wx1, wy1, wx2, wy2)
    prev_gray  = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    refresh_counter = 0
    next_rest_trigger = random.randint(14, 25)

    while IS_RUNNING:
        jittered_interval = REFRESH_INTERVAL + random.uniform(-0.8, 1.5)
        for _ in range(int(max(10, jittered_interval * 10))):
            if not IS_RUNNING: return
            time.sleep(0.1)

        click_refresh_region(rx1, ry1, rx2, ry2)
        refresh_counter += 1

        jittered_load_wait = PAGE_LOAD_WAIT + random.uniform(-0.4, 0.7)
        for _ in range(int(max(5, jittered_load_wait * 10))):
            if not IS_RUNNING: return
            time.sleep(0.1)

        curr_frame = capture_region(wx1, wy1, wx2, wy2)
        curr_gray  = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

        changed_px, regions, changed_rows, viz_bytes = analyze_changes(prev_gray, curr_gray, prev_frame, curr_frame)

        print(f"[{time.strftime('%H:%M:%S')}] 🔍 탐색 중...          ", end='\r', flush=True)

        if changed_px > (box_area * 0.5):
            print("\n[로딩/전환 감지] 스킵합니다.", flush=True)
            prev_gray = curr_gray
            continue

        if changed_px > CHANGE_MIN_PIXELS and regions:
            if len(regions) > 12:
                print(f"\n⚠️ [잔상/화면 밀림 방어] 무려 {len(regions)}개의 대량 변화 포착! 오류로 판단하여 스킵합니다.", flush=True)
                prev_gray = curr_gray
                continue

            valid_seats_to_click = []

            for (x, y, w, h) in regions:
                p_gray = cv2.resize(cv2.cvtColor(prev_frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY), (32, 32))
                c_gray = cv2.resize(cv2.cvtColor(curr_frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY), (32, 32))
                t1 = torch.tensor(p_gray, dtype=torch.float32).unsqueeze(0).unsqueeze(0) / 255.0
                t2 = torch.tensor(c_gray, dtype=torch.float32).unsqueeze(0).unsqueeze(0) / 255.0

                if model_backend is not None:
                    with torch.no_grad():
                        dist = torch.nn.functional.pairwise_distance(model_backend(t1, t2)[0], model_backend(t1, t2)[1]).item()
                    if dist > MODEL_DISTANCE_THRESHOLD:
                        valid_seats_to_click.append((x, y, w, h))
                else:
                    valid_seats_to_click.append((x, y, w, h))

            if valid_seats_to_click:
                print(f"\n[분석 알고리즘 통과] 신규 취소표 {len(valid_seats_to_click)}개 포착! 자리 잡으러 갑니다.", flush=True)

                clicked_count = 0
                for i, (rx, ry, rw, rh) in enumerate(valid_seats_to_click):
                    if i >= 4: break

                    offset_x = int(rw * random.uniform(-0.2, 0.2)) # 오차 범위 축소하여 정확도 업
                    offset_y = int(rh * random.uniform(-0.2, 0.2))
                    seat_cx = wx1 + rx + (rw // 2) + offset_x
                    seat_cy = wy1 + ry + (rh // 2) + offset_y

                    human_move_and_click(seat_cx, seat_cy)
                    clicked_count += 1

                    time.sleep(random.uniform(0.08, 0.15))

                fast_reaction_wait = random.uniform(0.12, 0.22)
                print(f"좌석 선택 완료! {fast_reaction_wait:.2f}초 만에 다음 단계 결제선 진입", flush=True)
                time.sleep(fast_reaction_wait)

                frame_before_click = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

                n_width = nx2 - nx1
                n_height = ny2 - ny1
                n_offset_x = int(n_width * random.uniform(-0.1, 0.1)) # 버튼 중심부 타격률 상향
                n_offset_y = int(n_height * random.uniform(-0.1, 0.1))
                next_cx = nx1 + (n_width // 2) + n_offset_x
                next_cy = ny1 + (n_height // 2) + n_offset_y

                human_move_and_click(next_cx, next_cy)

                print("다음 단계 진입 및 지연 팝업 다중 검증 중...", flush=True)
                time.sleep(0.85)

                frame_after_click = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
                gray_before_click = cv2.cvtColor(frame_before_click, cv2.COLOR_BGR2GRAY)
                gray_after_click = cv2.cvtColor(frame_after_click, cv2.COLOR_BGR2GRAY)

                popup_detected, score = detect_popup_simple(gray_before_click, gray_after_click)

                if popup_detected:
                    print(f"\n[방어 시스템 작동] 스코어({score:.1f}) 초과! 팝업 발생을 확정하여 해제합니다.", flush=True)
                    if WIN32_AVAILABLE:
                        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
                        time.sleep(0.05)
                        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
                    else:
                        pyautogui.press('enter')
                    time.sleep(0.5)

                    print("팝업 해제 완료! 시스템을 재개합니다.\n", flush=True)
                    prev_frame = capture_region(wx1, wy1, wx2, wy2)
                    prev_gray  = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                    continue
                else:
                    print(f"\n[안전 통과] 팝업 검증 점수 안전권({score:.1f})! 결제선 정상 진입 완료.", flush=True)

                    if choice == "2":
                        send_telegram_alert(chat_id, f"[분석 알고리즘 판독 완료!]\n\n 팝업을 해제 후 결제 단계 진입에 성공했습니다! 화면을 확인하세요.", viz_bytes)
                    else:
                        html = f"<html><body><h2 style='color:#e53e3e;'>분석 알고리즘 유효 좌석 선점 완료!</h2><p>정밀 판독 결과 진짜 취소표가 확인되어 클릭 및 결제선 진입을 성공적으로 실행했습니다.</p><br><p><b>[감시 포착 결과 스크린샷]</b></p><img src='cid:viz_img' style='max-width:100%; height:auto;'/></body></html>"
                        send_notification_email(user_email, "[티켓팅 알림] 검증 완료 및 자동 예약 성공!", html, viz_bytes)

                    print("\n자동화 시스템이 성공적으로 임무를 완수했습니다. 3초 후 프로그램을 완전히 종료합니다.", flush=True)
                    time.sleep(3)
                    os._exit(0)

        if refresh_counter >= next_rest_trigger:
            rest_duration = random.uniform(4.5, 8.5)
            print(f"\n[시스템 숨 고르기] 과부하 우회를 위해 {rest_duration:.2f}초간 휴식합니다.", flush=True)
            time.sleep(rest_duration)
            refresh_counter = 0
            next_rest_trigger = random.randint(14, 25)

        prev_frame = curr_frame
        prev_gray  = curr_gray

def select_region(label, color):
    coords = {'status': 'ok'}
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.4)
    root.attributes('-topmost', True)
    root.configure(bg='black')
    root.focus_force()

    canvas = tk.Canvas(root, cursor='cross', bg='black')
    canvas.pack(fill='both', expand=True)

    info_win = tk.Toplevel(root)
    info_win.overrideredirect(True)
    info_win.attributes('-topmost', True)
    info_win.attributes('-alpha', 0.95)
    info_win.configure(bg='#2d3748')

    iw, ih = 850, 110
    ix = (root.winfo_screenwidth() // 2) - (iw // 2)
    iy = 40
    info_win.geometry(f"{iw}x{ih}+{ix}+{iy}")

    tk.Label(info_win, text=label, font=('Malgun Gothic', 22, 'bold'), fg='#63b3ed', bg='#2d3748').pack(pady=(15, 5))
    tk.Label(info_win, text="[ESC]: 프로그램 즉시 종료  |  [Backspace] 연타 또는 [마우스 우클릭]: 이전 단계", font=('Malgun Gothic', 13, 'bold'), fg='#fbd38d', bg='#2d3748').pack()

    start_x = start_y = 0
    rect = None

    def close_all():
        info_win.destroy()
        root.destroy()

    def on_press(event): nonlocal start_x, start_y, rect; start_x, start_y = event.x, event.y; rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline=color, width=3)
    def on_drag(event): canvas.coords(rect, start_x, start_y, event.x, event.y)
    def on_release(event): coords.update({'x1': min(start_x, event.x), 'y1': min(start_y, event.y), 'x2': max(start_x, event.x), 'y2': max(start_y, event.y)}); close_all()

    def on_esc(event): coords['status'] = 'exit'; close_all()
    def on_back(event): coords['status'] = 'back'; close_all()

    canvas.bind('<ButtonPress-1>', on_press)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_release)

    root.bind_all('<Escape>', on_esc)
    root.bind_all('<BackSpace>', on_back)
    root.bind_all('<Button-3>', on_back)

    root.mainloop()

    if coords['status'] == 'exit': os._exit(0)
    return coords

def is_valid_email(email):
    """이메일 정규표현식 포맷 정밀 검증용 헬퍼 함수"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def main():
    global IS_RUNNING, stop_btn_root

    # 첫 구동 시 무조건 콘솔에 즉시 노출되는 대기 배너 시스템
    print("=" * 65, flush=True)
    print(" 티켓팅 고속 판독 및 다중 감시 시스템 프로토콜 가동", flush=True)
    print(" 프로그램 진입을 위해 키보드의 [ 엔터(Enter) ] 키를 눌러주세요.", flush=True)
    print("=" * 65, flush=True)
    input()  # 사용자 엔터 대기

    ai_model = load_deeplearning_model()

    # 수신 채널 검증 입력
    print("\n알림을 수신할 채널을 선택하세요. (1 또는 2)", flush=True)
    while True:
        choice = input("선택 (1: 이메일 / 2: 텔레그램): ").strip()
        if choice in ["1", "2"]:
            break
        print("잘못된 입력입니다. 숫자 1 또는 2만 입력 가능합니다.", flush=True)

    chat_id = None
    user_email = None

    # 이메일 오타 방어용 다중 유효성 검증 루프
    if choice == "2":
        chat_id = auto_detect_chat_id()
    else:
        while True:
            user_email = input("\n알림을 수신할 본인의 이메일 주소를 입력하세요: ").strip()

            # 1단계: 정규식 포맷 필터링
            if is_valid_email(user_email):
                # 2단계: 최종 사용자 재확인 단계 추가
                print(f"입력하신 주소 [ {user_email} ]가 정확히 맞습니까?", flush=True)
                confirm = input("맞다면 엔터(Enter), 오타가 있어 재입력하려면 'N'을 입력하세요: ").strip().upper()
                if confirm != 'N':
                    break
            else:
                print("올바른 이메일 형식이 아닙니다! (예: user@gmail.com) 다시 확인하세요.", flush=True)

    if not user_email and choice != "2":
        user_email = SENDER_EMAIL

    input("\n연동 완료! 브라우저 예매 창을 준비한 뒤 엔터를 누르면 타겟팅 드래그가 시작됩니다...")
    for i in range(3, 0, -1): print(f"{i}초 후 시작...", end='\r'); time.sleep(1)

    steps = [
        {"label": "① 감시할 좌석 구역 드래그", "color": "red"},
        {"label": "② 새로고침 버튼 드래그", "color": "cyan"},
        {"label": "③ 다음 단계 버튼 드래그", "color": "purple"}
    ]
    res_coords = [None, None, None]
    step_idx = 0

    while step_idx < 3:
        if step_idx > 0: time.sleep(0.5)

        coords = select_region(steps[step_idx]['label'], steps[step_idx]['color'])

        if coords['status'] == 'back':
            if step_idx == 0:
                print("\n이전 단계가 존재하지 않는 첫 단계입니다. 강제 종료하려면 ESC를 누르세요.", flush=True)
            else:
                print("\n이전 드래그 단계로 되돌아갑니다.", flush=True)
                step_idx -= 1
            continue

        res_coords[step_idx] = (coords['x1'], coords['y1'], coords['x2'], coords['y2'])
        step_idx += 1

    wx1, wy1, wx2, wy2 = res_coords[0]
    rx1, ry1, rx2, ry2 = res_coords[1]
    nx1, ny1, nx2, ny2 = res_coords[2]

    box_area = abs((wx2 - wx1) * (wy2 - wy1))
    time.sleep(1)

    threading.Thread(target=monitor_loop, args=(wx1, wy1, wx2, wy2, rx1, ry1, rx2, ry2, nx1, ny1, nx2, ny2, box_area, choice, chat_id, user_email, ai_model), daemon=True).start()

    stop_btn_root = tk.Tk()
    stop_btn_root.title("Alimi")
    stop_btn_root.attributes('-topmost', True)
    stop_btn_root.geometry("160x50+1200+80")
    tk.Button(stop_btn_root, text="시스템 중지", font=("Arial", 12, "bold"), bg="#e53e3e", fg="white", command=lambda: os._exit(0)).pack(fill="both", expand=True)
    stop_btn_root.mainloop()

if __name__ == "__main__":
    main()