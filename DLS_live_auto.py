import os
import time
import cv2
import numpy as np
import pyautogui
import win32gui
import win32ui
import win32api
import win32con
from ctypes import windll
import win32process

# === Config ===
IMAGE_FOLDER = 'imagesDLS'  # chứa START_LIVE.png, CONTINUE.png,...
CONFIDENCE = 0.71
CONFIDENCE_A_BUTTON = 0.5  # confidence cho A_BUTTON
WAIT_TIME = 1.0
OPTION_CLICK = 3  # 1: click A_BUTTON, 2: click ĐÚP vị trí ảo, 3: không click gì
pyautogui.FAILSAFE = False

def get_ldplayer_hwnd():
    hwnd = win32gui.FindWindow(None, None)
    while hwnd:
        title = win32gui.GetWindowText(hwnd)
        if "LDPlayer" in title:
            print(f"✅ Đã tìm thấy cửa sổ LDPlayer: {title}")
            return hwnd
        hwnd = win32gui.GetWindow(hwnd, 2)
    print("❌ Không tìm thấy cửa sổ LDPlayer")
    return None

def capture_window(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
    saveDC.SelectObject(saveBitMap)

    result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 1)
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype='uint8')
    img.shape = (height, width, 4)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    if result == 1:
        return img[..., :3]
    else:
        return None

def is_ldplayer_foreground(hwnd):
    """Kiểm tra xem LDPlayer có đang là cửa sổ foreground không"""
    return win32gui.GetForegroundWindow() == hwnd

def resize_template_to_fit(template, screenshot):
    """Resize ảnh mẫu nếu nó lớn hơn ảnh chụp màn hình"""
    if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
        ratio_h = screenshot.shape[0] / template.shape[0]
        ratio_w = screenshot.shape[1] / template.shape[1]
        ratio = min(ratio_h, ratio_w)
        new_size = (int(template.shape[1] * ratio), int(template.shape[0] * ratio))
        resized_template = cv2.resize(template, new_size)
        print(f"🔧 Resize ảnh mẫu còn {resized_template.shape[1]}x{resized_template.shape[0]}")
        return resized_template
    return template

def find_and_click_cv2(image_name, hwnd):
    image_path = os.path.join(IMAGE_FOLDER, image_name)
    template = cv2.imread(image_path)

    if template is None:
        print(f"⚠️ Không load được ảnh mẫu: {image_path}")
        return False

    screenshot = capture_window(hwnd)
    if screenshot is None:
        print("❌ Không chụp được cửa sổ LDPlayer.")
        return False

    template = resize_template_to_fit(template, screenshot)
    res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    print(f"🔍 So khớp {image_name} = {max_val:.2f}")

    match_threshold = CONFIDENCE_A_BUTTON if image_name == "A_BUTTON.png" else CONFIDENCE

    if max_val >= match_threshold:
        if not is_ldplayer_foreground(hwnd):
            print(f"⛔ LDPlayer không phải cửa sổ foreground, bỏ qua click {image_name}")
            return None  # Giá trị đặc biệt để vòng for biết dừng lại
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        center_x = left + max_loc[0] + template.shape[1] // 2
        center_y = top + max_loc[1] + template.shape[0] // 2
        pyautogui.click(center_x, center_y)
        print(f"🖱️ Click {image_name} tại ({center_x}, {center_y}) (match: {max_val:.2f})")
        return True
    else:
        if is_ldplayer_foreground(hwnd):  # chỉ in lỗi nếu đang foreground
            print(f"❌ Không tìm thấy {image_name} (match: {max_val:.2f})")
        return False


def find_cv2(image_name, hwnd):
    image_path = os.path.join(IMAGE_FOLDER, image_name)
    template = cv2.imread(image_path)

    if template is None:
        print(f"⚠️ Không load được ảnh mẫu: {image_path}")
        return False

    screenshot = capture_window(hwnd)
    if screenshot is None:
        print("❌ Không chụp được cửa sổ LDPlayer.")
        return False

    template = resize_template_to_fit(template, screenshot)

    res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    #print(f"🔍 So khớp {image_name} = {max_val:.2f}")

    return max_val >= CONFIDENCE

import time

def click_relative(hwnd, rel_x, rel_y): #click đúp
    if not is_ldplayer_foreground(hwnd):
        print(f"⛔ LDPlayer không phải foreground, bỏ qua click đúp")
        return

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    abs_x = int(left + width * rel_x)
    abs_y = int(top + height * rel_y)
    
    for _ in range(2):
        pyautogui.click(abs_x, abs_y)
        time.sleep(0.2)  # delay nhỏ giữa 2 lần click

    print(f"🖱️ Click đúp tại ({abs_x}, {abs_y})")
    print("👉 Đã click vào vị trí ảo thay cho nút A")



def auto_play_live():
    print("🚀 Bắt đầu auto LIVE...")
    hwnd = get_ldplayer_hwnd()
    if not hwnd:
        return

    while True:
        # ===== BƯỚC 1: START LIVE =====
        while True:
            if find_and_click_cv2("START_LIVE_2.png", hwnd):
                if find_and_click_cv2("NEW_EXIT_AD.png", hwnd):
                    print("🚫 Đã tắt quảng cáo")                 #check dp boot
                    time.sleep(1)
                    find_and_click_cv2("START_LIVE_2.png", hwnd)
                print("➡️ Đã click START_LIVE_2.png")
                time.sleep(2)
                find_and_click_cv2("START_LIVE.png", hwnd)
                break
            elif find_and_click_cv2("START_LIVE.png", hwnd):
                if find_and_click_cv2("NEW_EXIT_AD.png", hwnd):
                    print("🚫 Đã tắt quảng cáo")               #check dp boot
                    time.sleep(1)
                    find_and_click_cv2("START_LIVE_2.png", hwnd)
                print("➡️ Đã click START_LIVE.png")
                break
            else:
                print("⚠️ Chưa thấy START_LIVE nào, HÃY MỞ LDPLAYER hoặc thử lại sau 5s...")
                time.sleep(5)

        print("🚀 Đã click START LIVE")
        time.sleep(10)
        print("🎮 Bắt đầu spam trong trận đấu...")
        if find_cv2("FAILED_TO_CONNECT.png", hwnd):
            print("❌ Không thể kết nối, thoát...")
            find_and_click_cv2("OK_FAILED_TO_CONNECT.png", hwnd)
            time.sleep(2)
            if find_and_click_cv2("NEW_EXIT_AD.png", hwnd):
             print("🚫 Đã tắt quảng cáo")
             time.sleep(3)
            continue
        if find_and_click_cv2("YOU_WERE_DISCONNECTED.png", hwnd):
            print("❌ Lỗi kết nối, thoát...")
            time.sleep(2)
            if find_and_click_cv2("NEW_EXIT_AD.png", hwnd):
             print("🚫 Đã tắt quảng cáo")
             time.sleep(3)
            continue
        # ===== BƯỚC 1.5: Liên tục ấn A_BUTTON cho đến khi thấy nút HIGHLIGHTS hoặc các trạng thái đặc biệt =====
        while True:
            if find_cv2("MVP_PLAYER.png", hwnd):
                print("🎁 Đã phát hiện nút HIGHLIGHTS! Bắt đầu xử lý tiếp...")
                break

            if find_cv2("MATCH_END_EARLY.png", hwnd):
                find_and_click_cv2("OK_MATCH_END_EARLY.png", hwnd)
                time.sleep(3)
                print("➡️ Đã xử lý MATCH END EARLY (thua 10-0)")
                break

            if find_cv2("OPPONENT_DISCONNECTED.png", hwnd):
                find_and_click_cv2("OK_OPPONENT_DISCONNECTED.png", hwnd)
                time.sleep(3)
                print("➡️ Đã xử lý OPPONENT DICONNECTED (đối thủ thoát)")
                break
            
            if find_cv2("OPPONENT_CONCEDED.png", hwnd):
                find_and_click_cv2("OK_OPPONENT_CONCEDED.png", hwnd)
                time.sleep(3)
                print("➡️ Đã xử lý OPPONENT CONCEDED (đối thủ bỏ game)")
                break
            
            if (OPTION_CLICK==1) :
                # Nếu không thấy các trạng thái đặc biệt, tiếp tục spam A_BUTTON
                # Nếu không thấy các trạng thái đặc biệt, tiếp tục spam A_BUTTON
                for i in range(1, 7):
                    result = find_and_click_cv2(f"A_BUTTON_{i}.png", hwnd)
                    if result:  # True nghĩa là đã click
                        break
                    elif result is None:
                        break  # foreground không đúng, dừng luôn không check tiếp
                else:
                    print("❌ Không tìm thấy bất kỳ A_BUTTON nào.")
                time.sleep(2)
            if (OPTION_CLICK==2):
                click_relative(hwnd, 0.5, 0.2)  # click vào CHÍNH GIỮA
                time.sleep(0.2)  # delay nhỏ giữa các lần click
            
            if (OPTION_CLICK==3):
                pass
                time.sleep(6)

        print("🎁 Bắt đầu xử lý continue...")

        # ===== BƯỚC 2: CONTINUE LẦN 1 =====
        while not find_and_click_cv2("CONTINUE.png", hwnd):  # Lặp lại nếu không tìm thấy CONTINUE
            print("⚠️ Không tìm thấy CONTINUE, thử lại sau 4s...")
            time.sleep(5)

        print("➡️ Đã click CONTINUE lần 1")
        time.sleep(5)

        # ===== BƯỚC 3: CONTINUE LẦN 2 =====
        while not find_and_click_cv2("CONTINUE.png", hwnd):
            print("⚠️ Không tìm thấy CONTINUE, thử lại sau 4s...")
            time.sleep(3)

        print("➡️ Đã click CONTINUE lần 2")
        time.sleep(3)

        # ===== BƯỚC 4: XỬ LÝ CÁC TRẠNG THÁI KHÁC =====
        if find_cv2("MATCH_END_EARLY.png", hwnd):
            find_and_click_cv2("OK_MATCH_EARLY.png", hwnd)
            print("➡️ Đã xử lý MATCH END EARLY")
            time.sleep(3)

        if find_cv2("OPPONENT_FORFEIT.png", hwnd):
            find_and_click_cv2("OK_OPPONENT_FORFEIT.png", hwnd)
            print("➡️ Đã xử lý OPPONENT FORFEIT")
            time.sleep(3)
        
        # ===== BƯỚC 5: XỬ LÝ CUỐI =====
        if find_and_click_cv2("NEW_EXIT_AD.png", hwnd):
            print("🚫 Đã tắt quảng cáo")
            time.sleep(1)

        if find_and_click_cv2("NEW_EXIT_AD.png", hwnd):
            print("🚫 Đã tắt quảng cáo")
            time.sleep(1)
        if find_cv2("TIER_SUMMARY.png", hwnd):
            find_and_click_cv2("OK_TIER_SUMMARY.png", hwnd)
            print("➡️ Đã xử lý TIER SUMMARY")
            time.sleep(2)
        
        if find_and_click_cv2("NEW_EXIT_AD.png", hwnd):
            print("🚫 Đã tắt quảng cáo")
            time.sleep(1)
        

        print("🔁 Vòng chơi kết thúc, bắt đầu vòng tiếp theo...\n")
        time.sleep(WAIT_TIME)

        



# === CHẠY ===
if __name__ == "__main__":
    print("🟢 Tool đang chạy... (Ctrl+C để dừng)")
    auto_play_live()