import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import time

# -------------------------
# Bus Simulator - Full App
# -------------------------

# Global simulator state
bus_free = True
priority = "DMA"          # "CPU" or "DMA" when using priority mode
mode = "Manual"           # "Manual" or "Auto"
arb_mode = "Priority"     # "Priority" or "RoundRobin"
queue = []                # request queue: items are ("CPU"|"DMA", timestamp/id)
cpu_count = 0
dma_count = 0
transfer_speed_ms = 30    # speed used by progress bar increments (lower = faster)
auto_gen_interval = 2000  # ms between auto-generated requests
paused = False
rr_turn = "CPU"           # next turn for round-robin arbitration

# GUI root
root = tk.Tk()
root.title("Bus-Based System — Advanced Simulator")
root.geometry("1100x720")
root.configure(bg="#111216")

# -------------------------
# Visual Canvas (Main)
# -------------------------
canvas = tk.Canvas(root, width=1000, height=360, bg="#0f1720", highlightthickness=0)
canvas.pack(pady=(12,6))

# Draw main boxes
def draw_components():
    canvas.delete("comp")
    # CPU block (left)
    canvas.create_rectangle(60, 110, 220, 230, fill="#0ea5e9", outline="#083d56", width=3, tags="comp")
    canvas.create_text(140, 95, text="CPU", font=("Helvetica", 14, "bold"), fill="white", tags="comp")
    canvas.create_text(140, 170, text="(Master 1)", font=("Helvetica", 10), fill="#e6f7ff", tags="comp")

    # DMA block (right)
    canvas.create_rectangle(780, 110, 940, 230, fill="#fb923c", outline="#7a3e12", width=3, tags="comp")
    canvas.create_text(860, 95, text="DMA", font=("Helvetica", 14, "bold"), fill="white", tags="comp")
    canvas.create_text(860, 170, text="(Master 2)", font=("Helvetica", 10), fill="#fff0e6", tags="comp")

    # Memory / I-O block (top center)
    canvas.create_rectangle(380, 18, 620, 88, fill="#fde047", outline="#b07c00", width=3, tags="comp")
    canvas.create_text(500, 40, text="MEMORY / I-O", font=("Helvetica", 13, "bold"), fill="#2b2b2b", tags="comp")
    canvas.create_text(500, 60, text="(Target Device)", font=("Helvetica", 9), fill="#2b2b2b", tags="comp")

    # Bus block (bottom center)
    canvas.create_rectangle(380, 260, 620, 320, fill="#374151", outline="#0b0e11", width=3, tags="comp")
    canvas.create_text(500, 290, text="SYSTEM BUS", font=("Helvetica", 13, "bold"), fill="white", tags="comp")

    # initial arrows (thin lines)
    canvas.create_line(220, 170, 380, 280, arrow=tk.LAST, width=4, fill="#94a3b8", tags="cpu_arrow")
    canvas.create_line(780, 170, 620, 280, arrow=tk.LAST, width=4, fill="#94a3b8", tags="dma_arrow")
    canvas.create_line(500, 260, 500, 100, arrow=tk.LAST, width=4, fill="#94a3b8", tags="bus_mem_arrow")

draw_components()

# -------------------------
# Controls / Left Panel
# -------------------------
controls_frame = tk.Frame(root, bg="#0b1220")
controls_frame.pack(fill="x", pady=(6,8))

left_controls = tk.Frame(controls_frame, bg="#0b1220")
left_controls.grid(row=0, column=0, padx=12, sticky="nw")

# Mode controls
mode_label = tk.Label(left_controls, text="Mode:", bg="#0b1220", fg="#c7d2fe", font=("Helvetica", 10, "bold"))
mode_label.grid(row=0, column=0, sticky="w", pady=2)
mode_var = tk.StringVar(value=mode)
mode_menu = ttk.Combobox(left_controls, textvariable=mode_var, values=["Manual", "Auto"], width=10, state="readonly")
mode_menu.grid(row=0, column=1, padx=6)
mode_menu.bind("<<ComboboxSelected>>", lambda e: toggle_mode(mode_var.get()))

# Arbitration mode (priority or round-robin)
arb_label = tk.Label(left_controls, text="Arbitration:", bg="#0b1220", fg="#c7d2fe", font=("Helvetica", 10, "bold"))
arb_label.grid(row=1, column=0, sticky="w", pady=2)
arb_var = tk.StringVar(value=arb_mode)
arb_menu = ttk.Combobox(left_controls, textvariable=arb_var, values=["Priority", "RoundRobin"], width=12, state="readonly")
arb_menu.grid(row=1, column=1, padx=6)
arb_menu.bind("<<ComboboxSelected>>", lambda e: set_arb_mode(arb_var.get()))

# Priority selection (when in Priority mode)
prio_label = tk.Label(left_controls, text="Priority:", bg="#0b1220", fg="#c7d2fe", font=("Helvetica", 10, "bold"))
prio_label.grid(row=2, column=0, sticky="w", pady=2)
prio_var = tk.StringVar(value=priority)
prio_menu = ttk.Combobox(left_controls, textvariable=prio_var, values=["CPU", "DMA"], width=8, state="readonly")
prio_menu.grid(row=2, column=1, padx=6)
prio_menu.bind("<<ComboboxSelected>>", lambda e: set_priority(prio_var.get()))

# Speed slider
speed_label = tk.Label(left_controls, text="Transfer Speed:", bg="#0b1220", fg="#c7d2fe", font=("Helvetica", 10, "bold"))
speed_label.grid(row=3, column=0, sticky="w", pady=2)
speed_slider = tk.Scale(left_controls, from_=5, to=100, orient="horizontal", bg="#0b1220", fg="white",
                        troughcolor="#0f1720", length=200, command=lambda v: set_speed(v))
speed_slider.set(transfer_speed_ms)
speed_slider.grid(row=3, column=1, padx=6, pady=4)

# Auto gen interval
auto_label = tk.Label(left_controls, text="Auto gen ms:", bg="#0b1220", fg="#c7d2fe", font=("Helvetica", 10, "bold"))
auto_label.grid(row=4, column=0, sticky="w", pady=2)
auto_entry = tk.Entry(left_controls, width=8)
auto_entry.insert(0, str(auto_gen_interval))
auto_entry.grid(row=4, column=1, padx=6)

# Buttons: Manual request, toggles
btn_frame = tk.Frame(left_controls, bg="#0b1220")
btn_frame.grid(row=5, column=0, columnspan=2, pady=(6,0))

cpu_req_btn = tk.Button(btn_frame, text="CPU Request", bg="#06b6d4", fg="black", width=14, command=lambda: enqueue_request("CPU"))
cpu_req_btn.grid(row=0, column=0, padx=6, pady=4)

dma_req_btn = tk.Button(btn_frame, text="DMA Request", bg="#fb923c", fg="black", width=14, command=lambda: enqueue_request("DMA"))
dma_req_btn.grid(row=0, column=1, padx=6, pady=4)

auto_toggle_btn = tk.Button(btn_frame, text="Start Auto", bg="#2dd4bf", fg="black", width=14, command=lambda: toggle_auto())
auto_toggle_btn.grid(row=1, column=0, padx=6, pady=4)

pause_btn = tk.Button(btn_frame, text="Pause", bg="#f97316", fg="black", width=14, command=lambda: toggle_pause())
pause_btn.grid(row=1, column=1, padx=6, pady=4)

# Save and Reset
misc_frame = tk.Frame(left_controls, bg="#0b1220")
misc_frame.grid(row=6, column=0, columnspan=2, pady=(8,2))

save_btn = tk.Button(misc_frame, text="Save Log", width=14, bg="#7c3aed", fg="white", command=lambda: save_log())
save_btn.grid(row=0, column=0, padx=6, pady=4)

reset_btn = tk.Button(misc_frame, text="Reset Stats", width=14, bg="#ef4444", fg="white", command=lambda: reset_stats())
reset_btn.grid(row=0, column=1, padx=6, pady=4)

# -------------------------
# Right Panel: Queue, Stats, Progress, Log
# -------------------------
right_frame = tk.Frame(controls_frame, bg="#071127")
right_frame.grid(row=0, column=1, padx=12, sticky="ne")

# Request Queue visualization
q_label = tk.Label(right_frame, text="Request Queue", bg="#071127", fg="#93c5fd", font=("Helvetica", 11, "bold"))
q_label.pack(anchor="w")
queue_listbox = tk.Listbox(right_frame, width=40, height=6, bg="#0b1220", fg="white", font=("Courier", 10))
queue_listbox.pack(pady=(4,8))

# Stats
stats_box = tk.Frame(right_frame, bg="#071127")
stats_box.pack(fill="x", pady=(2,8))

cpu_stat_label = tk.Label(stats_box, text="CPU Wins: 0", bg="#071127", fg="#93c5fd", font=("Helvetica", 11, "bold"))
cpu_stat_label.pack(anchor="w", pady=2)
dma_stat_label = tk.Label(stats_box, text="DMA Wins: 0", bg="#071127", fg="#fca5a5", font=("Helvetica", 11, "bold"))
dma_stat_label.pack(anchor="w", pady=2)

# Progress bar for transfer
transfer_label = tk.Label(right_frame, text="Transfer Progress", bg="#071127", fg="#93c5fd", font=("Helvetica", 11, "bold"))
transfer_label.pack(anchor="w", pady=(6,2))
progress_var = tk.DoubleVar(value=0)
progress = ttk.Progressbar(right_frame, orient="horizontal", length=360, mode="determinate", variable=progress_var, maximum=100)
progress.pack()

# Detailed log text (separate)
log_title = tk.Label(root, text="Event Log", bg="#111216", fg="#c7d2fe", font=("Helvetica", 11, "bold"))
log_title.pack(anchor="w", padx=12)
log_frame = tk.Frame(root, bg="#0b1220")
log_frame.pack(fill="both", padx=12, pady=(6,12), expand=False)

log_text = tk.Text(log_frame, height=10, bg="#010409", fg="#7fffd4", font=("Courier", 10))
log_text.pack(side="left", fill="both", expand=True)
log_scroll = tk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
log_scroll.pack(side="right", fill="y")
log_text.config(yscrollcommand=log_scroll.set)

def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
    log_text.see(tk.END)

# -------------------------
# Simulator Functions
# -------------------------
def refresh_queue_display():
    queue_listbox.delete(0, tk.END)
    for idx, (who, nid) in enumerate(queue):
        queue_listbox.insert(tk.END, f"{idx+1}. {who} (id:{nid})")

def enqueue_request(who):
    if paused:
        log(f"Simulator paused — cannot enqueue {who}")
        return
    # create unique id
    nid = int(time.time() * 1000) % 100000
    queue.append((who, nid))
    log(f"{who} enqueued (id:{nid})")
    refresh_queue_display()
    # If bus is free and manual mode, process immediately
    if bus_free and mode == "Manual":
        root.after(50, process_next_request)

def process_next_request():
    global bus_free, queue, rr_turn
    if paused:
        return
    if not queue:
        return
    # If bus busy, do nothing
    if not bus_free:
        return
    # Determine winner based on arbitration mode
    if arb_mode == "Priority":
        # If one of queue has priority master at front anywhere, pick first occurrence of priority master,
        # otherwise pick first in queue
        winner_index = None
        for i, (who, nid) in enumerate(queue):
            if who == priority:
                winner_index = i
                break
        if winner_index is None:
            winner_index = 0
    else:  # RoundRobin
        # pick first request that matches rr_turn if exists, else earliest arrival
        winner_index = None
        for i, (who, nid) in enumerate(queue):
            if who == rr_turn:
                winner_index = i
                break
        if winner_index is None:
            winner_index = 0

    who, nid = queue.pop(winner_index)
    refresh_queue_display()
    # If round-robin, toggle turn
    if arb_mode == "RoundRobin":
        rr_turn = "DMA" if rr_turn == "CPU" else "CPU"
    # grant bus
    grant_bus(who, nid)

def grant_bus(master, nid):
    global bus_free
    bus_free = False
    canvas.itemconfig("cpu_arrow", fill="#94a3b8")
    canvas.itemconfig("dma_arrow", fill="#94a3b8")
    canvas.itemconfig("bus_mem_arrow", fill="#94a3b8")
    # color highlight of the bus
    canvas.itemconfig("comp", state="normal")
    canvas.itemconfig("cpu_arrow", state="normal")
    canvas.itemconfig("dma_arrow", state="normal")
    canvas.itemconfig("bus_mem_arrow", state="normal")

    # show bus busy color
    canvas.itemconfig("all", state="normal")
    canvas.itemconfig("cpu_arrow")
    canvas.itemconfig("dma_arrow")
    canvas.itemconfig("bus_mem_arrow")
    canvas.itemconfig("comp")

    canvas.itemconfig(3, fill="#10b981")  # try to color the bus rectangle - index might vary, adjust visually below
    # Instead, find and color the BUS rectangle by coordinates
    # We'll color any rectangle near the bottom center
    for item in canvas.find_all():
        coords = canvas.coords(item)
        if len(coords) == 4:
            x1,y1,x2,y2 = coords
            # bus area approximate
            if 360 <= x1 <= 400 and 260 <= y1 <= 300:
                canvas.itemconfig(item, fill="#10b981")
    log(f"{master} (id:{nid}) granted BUS")
    update_stats(master)
    animate_transfer(master, nid)

def animate_transfer(master, nid):
    """Visual: flash master->bus arrow, then progress bar, then bus->mem arrow"""
    # highlight arrow from master to bus
    arrow = "cpu_arrow" if master == "CPU" else "dma_arrow"
    color = "#06b6d4" if master == "CPU" else "#fb923c"
    # flash arrow several times
    times = 8
    for i in range(times):
        root.after(i * 120, lambda a=arrow, c=color: canvas.itemconfig(a, fill=c))
        root.after(i * 120 + 60, lambda a=arrow: canvas.itemconfig(a, fill="#94a3b8"))

    # progress bar animation (simulate transfer duration)
    total_steps = 100
    step_ms = max(5, int(transfer_speed_ms))  # from slider; lower => faster
    # Reset progress
    progress_var.set(0)
    # After arrow flashing, start filling progress:
    start_delay = times * 120 + 80
    for s in range(total_steps + 1):
        root.after(start_delay + s * step_ms, lambda val=s: progress_var.set(val))
    # After progress completes, flash bus->mem arrow
    mem_flash_delay = start_delay + total_steps * step_ms + 80
    for i in range(8):
        root.after(mem_flash_delay + i * 120, lambda: canvas.itemconfig("bus_mem_arrow", fill="gold"))
        root.after(mem_flash_delay + i * 120 + 60, lambda: canvas.itemconfig("bus_mem_arrow", fill="#94a3b8"))
    # After everything, release bus and process next
    total_time = mem_flash_delay + 8 * 120 + 80
    root.after(total_time, lambda m=master, idn=nid: finish_transfer(m, idn))

def finish_transfer(master, nid):
    global bus_free
    bus_free = True
    # reset bus color back to grey
    for item in canvas.find_all():
        coords = canvas.coords(item)
        if len(coords) == 4:
            x1,y1,x2,y2 = coords
            if 360 <= x1 <= 400 and 260 <= y1 <= 300:
                canvas.itemconfig(item, fill="#374151")
    progress_var.set(0)
    log(f"{master} (id:{nid}) finished transfer and released BUS\n")
    # Automatically process next queued request if any
    root.after(120, process_next_request)

def update_stats(master):
    global cpu_count, dma_count
    if master == "CPU":
        cpu_count += 1
        cpu_stat_label.config(text=f"CPU Wins: {cpu_count}")
    else:
        dma_count += 1
        dma_stat_label.config(text=f"DMA Wins: {dma_count}")

# -------------------------
# Mode / Control Helpers
# -------------------------
def toggle_mode(new_mode):
    global mode
    mode = new_mode
    log(f"Mode set to: {mode}")
    if mode == "Auto":
        # start auto generation
        start_auto_requests()
    else:
        stop_auto_requests()

def set_arb_mode(new_mode):
    global arb_mode
    arb_mode = new_mode
    log(f"Arbitration mode set to: {arb_mode}")

def set_priority(p):
    global priority
    priority = p
    log(f"Priority set to: {priority}")

def set_speed(v):
    global transfer_speed_ms
    try:
        transfer_speed_ms = int(v)
    except:
        transfer_speed_ms = 30

def toggle_auto():
    global mode
    if mode != "Auto":
        mode_var.set("Auto")
        toggle_mode("Auto")
        auto_toggle_btn.config(text="Stop Auto", bg="#ef4444")
    else:
        mode_var.set("Manual")
        toggle_mode("Manual")
        auto_toggle_btn.config(text="Start Auto", bg="#2dd4bf")

# -------------------------
# Auto Request Generation
# -------------------------
auto_job_id = None
def start_auto_requests():
    global auto_job_id
    try:
        interval = int(auto_entry.get())
    except:
        interval = auto_gen_interval
    def gen():
        if paused:
            schedule_next()
            return
        who = random.choice(["CPU","DMA"])
        enqueue_request(who)
        schedule_next()
    def schedule_next():
        global auto_job_id
        auto_job_id = root.after(interval, gen)
    # kick off
    if auto_job_id:
        root.after_cancel(auto_job_id)
    schedule_next()
    log("Auto request generation started.")

def stop_auto_requests():
    global auto_job_id
    if auto_job_id:
        try:
            root.after_cancel(auto_job_id)
        except:
            pass
        auto_job_id = None
    log("Auto request generation stopped.")

# -------------------------
# Pause / Resume
# -------------------------
def toggle_pause():
    global paused
    paused = not paused
    if paused:
        pause_btn.config(text="Resume", bg="#10b981")
        log("Simulator paused")
    else:
        pause_btn.config(text="Pause", bg="#f97316")
        log("Simulator resumed")
        # attempt to continue processing
        root.after(80, process_next_request)

# -------------------------
# Save log / Reset stats
# -------------------------
def save_log():
    txt = log_text.get("1.0", tk.END)
    if not txt.strip():
        messagebox.showinfo("Save Log", "No log to save.")
        return
    path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    messagebox.showinfo("Save Log", f"Log saved to:\n{path}")

def reset_stats():
    global cpu_count, dma_count, queue
    if messagebox.askyesno("Reset", "Reset statistics and clear queue?"):
        cpu_count = 0
        dma_count = 0
        cpu_stat_label.config(text="CPU Wins: 0")
        dma_stat_label.config(text="DMA Wins: 0")
        queue.clear()
        refresh_queue_display()
        log("Statistics and queue reset.")

# -------------------------
# Initialize / bind actions
# -------------------------
def on_close():
    stop_auto_requests()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# Show helpful starting message
log("Bus-Based System Simulator started.")
log("Use mode=Auto to generate random requests, or Manual to click CPU / DMA Request.")
log("Arbitration: Priority (CPU/DMA) or RoundRobin. Adjust speed & auto interval for demo.")

# Kick initial UI update
refresh_queue_display()

# Ensure periodic attempt to process queue (in case btns add while bus free)
def periodic_processor():
    if not paused and bus_free and queue:
        process_next_request()
    root.after(150, periodic_processor)

periodic_processor()

# Run the App
root.mainloop()
