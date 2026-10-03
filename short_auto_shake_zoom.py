import os
import subprocess
import random
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json

# ================= CONFIG =================
BASE = os.path.dirname(os.path.abspath(__file__))

IMG_FOLDER = os.path.join(BASE, "Images")
AUD_FOLDER = os.path.join(BASE, "Audio")
OVR_FOLDER = os.path.join(BASE, "Overlay")
OUT_FOLDER = os.path.join(BASE, "Output")

WIDTH = 1080
HEIGHT = 1920
FPS = 30
MIN_DUR = 35
MAX_DUR = 55

for f in [IMG_FOLDER, AUD_FOLDER, OVR_FOLDER, OUT_FOLDER]:
    os.makedirs(f, exist_ok=True)

# ================= GET AUDIO DURATION =================
def get_audio_duration(path):
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(r.stdout)
    return float(data["format"]["duration"])

# ================= BUILD VIDEO =================
def build_video(image, audio, start_time, duration, overlays, index):

    img_path = os.path.join(IMG_FOLDER, image)
    audio_path = os.path.join(AUD_FOLDER, audio)

    audio_name = os.path.splitext(audio)[0]
    output_name = f"{audio_name}_{index+1}.mp4"
    output_path = os.path.join(OUT_FOLDER, output_name)

    cmd = ["ffmpeg", "-y"]

    # IMAGE
    cmd += [
        "-loop", "1",
        "-t", str(duration),
        "-i", img_path
    ]

    # AUDIO CUT
    cmd += [
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", audio_path
    ]

    # OVERLAY RANDOM
    overlay_index = None
    if overlays:
        ov = random.choice(overlays)
        cmd += [
            "-stream_loop", "-1",
            "-i", os.path.join(OVR_FOLDER, ov)
        ]
        overlay_index = 2

    # SHAKE + ZOOM
    filter_complex = (
        "[0:v]"
        "scale=2200:-1,"
        "zoompan="
        "z='1+0.003*sin(on/6)':"
        "x='iw/2-(iw/zoom/2)+40*sin(2*PI*on/15)':"
        "y='ih/2-(ih/zoom/2)+40*cos(2*PI*on/17)':"
        f"d={int(duration*FPS)}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS},"
        "setsar=1[vbase]"
    )

    if overlay_index is not None:
        filter_complex += (
            f";[{overlay_index}:v]scale={WIDTH}:{HEIGHT},setsar=1[ov];"
            "[vbase][ov]overlay=0:0:shortest=1[vout]"
        )
        final_video = "[vout]"
    else:
        final_video = "[vbase]"

    cmd += [
        "-filter_complex", filter_complex,
        "-map", final_video,
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-shortest",
        output_path
    ]

    subprocess.run(cmd)

# ================= MAIN =================
def start_render():

    images_all = [f for f in os.listdir(IMG_FOLDER)
                  if f.lower().endswith((".jpg", ".png", ".jpeg"))]

    audios_all = [f for f in os.listdir(AUD_FOLDER)
                  if f.lower().endswith((".mp3", ".wav", ".m4a"))]

    overlays_all = [f for f in os.listdir(OVR_FOLDER)
                    if f.lower().endswith((".mp4", ".mov", ".webm", ".png"))]

    try:
        img_count = int(img_entry.get())
        aud_count = int(aud_entry.get())
        ovr_count = int(ovr_entry.get())
    except:
        messagebox.showerror("Error", "Masukkan angka valid")
        return

    if img_count > len(images_all) or aud_count > len(audios_all):
        messagebox.showerror("Error", "Jumlah melebihi isi folder")
        return

    selected_images = random.sample(images_all, img_count)
    selected_audios = random.sample(audios_all, aud_count)
    selected_overlays = random.sample(overlays_all, min(ovr_count, len(overlays_all)))

    progress["maximum"] = len(selected_images)

    # ===== SLOT UNIK PER AUDIO =====
    audio_slots = {}

    for audio in selected_audios:
        total_dur = get_audio_duration(os.path.join(AUD_FOLDER, audio))
        duration = random.uniform(MIN_DUR, MAX_DUR)

        step = duration * 0.7
        start = total_dur * 0.2
        slots = []

        while start + duration <= total_dur:
            slots.append((start, duration))
            start += step

        random.shuffle(slots)
        audio_slots[audio] = slots

    def render_thread():
        for i, img in enumerate(selected_images):

            audio = selected_audios[i % len(selected_audios)]

            if audio_slots[audio]:
                start_time, dur = audio_slots[audio].pop()
            else:
                total_dur = get_audio_duration(os.path.join(AUD_FOLDER, audio))
                dur = random.uniform(MIN_DUR, MAX_DUR)
                start_time = random.uniform(total_dur*0.2, total_dur-dur)

            build_video(img, audio, start_time, dur, selected_overlays, i)

            progress["value"] = i + 1
            percent_label.config(text=f"{int((i+1)/len(selected_images)*100)}%")
            root.update_idletasks()

        os.startfile(OUT_FOLDER)

    threading.Thread(target=render_thread, daemon=True).start()

# ================= GUI =================
root = tk.Tk()
root.title("AUTO SHORT PRO FINAL")
root.geometry("420x420")
root.resizable(False, False)

tk.Label(root, text=f"Gambar tersedia: {len(os.listdir(IMG_FOLDER))}").pack()
img_entry = tk.Entry(root)
img_entry.insert(0, "10")
img_entry.pack()

tk.Label(root, text=f"Audio tersedia: {len(os.listdir(AUD_FOLDER))}").pack()
aud_entry = tk.Entry(root)
aud_entry.insert(0, "3")
aud_entry.pack()

tk.Label(root, text=f"Overlay tersedia: {len(os.listdir(OVR_FOLDER))}").pack()
ovr_entry = tk.Entry(root)
ovr_entry.insert(0, "2")
ovr_entry.pack()

tk.Button(root, text="RENDER",
          command=start_render,
          bg="green", fg="white").pack(pady=20)

progress = ttk.Progressbar(root, length=300)
progress.pack()

percent_label = tk.Label(root, text="0%")
percent_label.pack()

root.mainloop()
