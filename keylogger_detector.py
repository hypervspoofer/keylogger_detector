import psutil
import win32gui
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os

DARK_MODE_DEFAULT = True
BASIC_THRESHOLD = 90
AGGRESSIVE_THRESHOLD = 50
MIN_SCAN_SECONDS = 5

SELF_PID = os.getpid()
EXCLUDE_PIDS = {0, 4, SELF_PID}

def has_visible_window(pid):
    def cb(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            _, p = win32gui.GetWindowThreadProcessId(hwnd)
            if p == pid:
                result.append(hwnd)
        return True
    result = []
    try:
        win32gui.EnumWindows(cb, result)
    except:
        pass
    return bool(result)

def analyze_process(proc, aggressive):
    if proc.pid in EXCLUDE_PIDS:
        return None

    score = 0
    reasons = []
    try:
        name = proc.name().lower()
        threads = proc.num_threads()
        uptime = time.time() - proc.create_time()
        cpu = proc.cpu_percent(interval=0.1)

        if not has_visible_window(proc.pid):
            score += 20
            reasons.append("Hidden background process")

        score += min(threads * 5, 20)
        if threads >= 4:
            reasons.append(f"High thread count ({threads})")

        score += min(uptime / 5, 25)
        if uptime > 20:
            reasons.append("Long‑running background process")

        score += min(cpu * 30, 15)
        if cpu > 0.3:
            reasons.append("Sustained background CPU activity")

        if aggressive and name == "python.exe":
            score += 25
            reasons.append("Scripted runtime running without UI")

        score = min(int(score), 100)
    except:
        return None

    return score, reasons

def confirm_terminate(pid, button):
    # Popup in dark mode
    popup = tk.Toplevel(app)
    popup.configure(bg="#1e1e1e")
    popup.title("Confirm End Task")
    popup.geometry("350x150")
    popup.resizable(False, False)
    
    tk.Label(
        popup,
        text=f"Are you sure you want to end PID {pid}?\nThis may break your system or unsaved work!",
        bg="#1e1e1e",
        fg="white",
        wraplength=320,
        justify="center",
        font=("Segoe UI", 10)
    ).pack(pady=20)
    
    btn_frame = tk.Frame(popup, bg="#1e1e1e")
    btn_frame.pack(pady=10)
    
    def cancel():
        popup.destroy()
    
    def confirm():
        try:
            psutil.Process(pid).terminate()
            button.config(text="Task Ended", bg="#555555", state="disabled")
        except Exception as e:
            messagebox.showerror("Failed", f"Could not terminate PID {pid}\n{e}")
        popup.destroy()
    
    tk.Button(btn_frame, text="No", width=12, command=cancel).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Yes, I understand", width=16, command=confirm).pack(side="left", padx=5)

def scan_system(aggressive, progress_cb):
    start = time.time()
    findings = []
    procs = list(psutil.process_iter())
    total = len(procs)

    for i, p in enumerate(procs, start=1):
        progress_cb((i / total) * 70)
        result = analyze_process(p, aggressive)
        if result:
            score, reasons = result
            threshold = AGGRESSIVE_THRESHOLD if aggressive else BASIC_THRESHOLD
            if score >= threshold:
                findings.append((p.name(), p.pid, score, reasons))

    while time.time() - start < MIN_SCAN_SECONDS:
        elapsed = time.time() - start
        progress_cb(70 + (elapsed / MIN_SCAN_SECONDS) * 30)
        time.sleep(0.05)

    progress_cb(100)
    findings.sort(key=lambda x: x[2], reverse=True)
    return findings

def start_scan(aggressive):
    for w in result_inner.winfo_children():
        w.destroy()

    status.config(text="Scanning…")
    progress["value"] = 0
    basic_btn.config(state="disabled")
    aggressive_btn.config(state="disabled")

    def worker():
        results = scan_system(
            aggressive,
            lambda v: progress.after(0, progress.configure, value=v)
        )

        if results:
            status.config(text="⚠ Suspicious behavior detected")
            for name, pid, score, reasons in results:
                box = tk.Frame(result_inner, bg=bg, bd=1, relief="solid")
                box.pack(fill="x", pady=4, padx=5)

                tk.Label(
                    box,
                    text=f"{name} | PID {pid} | Risk {score}%",
                    bg=bg,
                    fg=fg,
                    font=("Segoe UI", 10, "bold")
                ).pack(anchor="w", padx=5, pady=2)

                for r in reasons:
                    tk.Label(
                        box,
                        text="• " + r,
                        bg=bg,
                        fg=fg,
                        font=("Segoe UI", 9)
                    ).pack(anchor="w", padx=15)

                end_btn = tk.Button(
                    box,
                    text="End Task",
                    fg="white",
                    bg="#c0392b"
                )
                end_btn.config(command=lambda p=pid, b=end_btn: confirm_terminate(p, b))
                end_btn.pack(anchor="e", padx=8, pady=5)

            canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        else:
            status.config(text="✅ No high‑risk behavior detected")
            tk.Label(
                result_inner,
                text="No processes exceeded detection threshold.",
                bg=bg,
                fg=fg
            ).pack(pady=20)
            canvas.unbind_all("<MouseWheel>")

        basic_btn.config(state="normal")
        aggressive_btn.config(state="normal")

    threading.Thread(target=worker, daemon=True).start()

def tooltip(widget, text):
    tip = tk.Toplevel(widget)
    tip.withdraw()
    tip.overrideredirect(True)
    label = tk.Label(tip, text=text, bg="#333", fg="white", padx=6, pady=3)
    label.pack()

    widget.bind("<Enter>", lambda e: (tip.geometry(f"+{e.x_root+10}+{e.y_root+10}"), tip.deiconify()))
    widget.bind("<Leave>", lambda e: tip.withdraw())

def show_info():
    messagebox.showinfo(
        "About This Tool",
        "Keylogger Detection Tool v1.0\n\n"
        "Created for testing and educational purposes.\n"
        "Analyzes running processes and assigns risk scores.\n"
        "Higher scores indicate more suspicious behavior.\n"
        "Use responsibly."
    )

app = tk.Tk()
app.title("Keylogger Detection Tool")
app.geometry("800x600")
app.resizable(False, False)

bg = "#1e1e1e"
fg = "#ffffff"
app.configure(bg=bg)

tk.Label(app, text="Keylogger Detection Tool", font=("Segoe UI", 16), bg=bg, fg=fg).pack(pady=10)

controls = tk.Frame(app, bg=bg)
controls.pack()

basic_row = tk.Frame(controls, bg=bg)
basic_row.pack()
basic_btn = tk.Button(basic_row, text="Basic Scan", width=18, command=lambda: start_scan(False))
basic_btn.pack(side="left")
basic_i = tk.Label(basic_row, text=" ℹ", fg="#5dade2", bg=bg, cursor="question_arrow")
basic_i.pack(side="left")
tooltip(basic_i, "Honest detection.\nLow false positives.\nMay miss advanced threats.")

aggressive_row = tk.Frame(controls, bg=bg)
aggressive_row.pack(pady=6)
aggressive_btn = tk.Button(
    aggressive_row,
    text="Aggressive Scan (Recommended)",
    width=22,
    command=lambda: start_scan(True)
)
aggressive_btn.pack(side="left")
aggressive_i = tk.Label(aggressive_row, text=" ℹ", fg="#e67e22", bg=bg, cursor="question_arrow")
aggressive_i.pack(side="left")
tooltip(aggressive_i, "Heuristic detection.\nMay flag legitimate processes.\nHigher false positives.")

progress = ttk.Progressbar(app, length=720)
progress.pack(pady=10)

status = tk.Label(app, text="Idle", bg=bg, fg=fg, font=("Segoe UI", 11))
status.pack()

canvas = tk.Canvas(app, bg=bg, highlightthickness=0)
scrollbar = ttk.Scrollbar(app, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

result_inner = tk.Frame(canvas, bg=bg)
canvas.create_window((0, 0), window=result_inner, anchor="nw")

result_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

info_icon = tk.Label(app, text="ℹ", fg="#5dade2", bg=bg, cursor="hand2")
info_icon.place(x=120, y=575)
info_icon.bind("<Button-1>", lambda e: show_info())

tk.Label(app, text="Made by Kernel", bg=bg, fg="gray").place(x=10, y=575)

app.mainloop()

