# gui/window.py
import tkinter as tk
from PIL import Image, ImageTk
import threading
import queue

from jarvis.assistant import JarvisAssistant
from jarvis.paths import paths


def run_app():
    # ---- base window size ----
    WINDOW_WIDTH = 280
    WINDOW_BASE_HEIGHT = 350

    root = tk.Tk()
    root.title("Arjun")
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_BASE_HEIGHT}")

    current_wake_name = "Arjun"
    base_status_height = None  # will be measured after first status

    BG_COLOR = "#2B2B2B"
    TEXT_COLOR = "#E0E0E0"
    ACCENT_COLOR = "#A0DDEE"
    QUIT_COLOR = "#C04040"
    QUIT_HOVER = "#D05050"

    root.configure(bg=BG_COLOR)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.95)

    gui_queue = queue.Queue()

    def update_gui_status(text):
        gui_queue.put(text)

    # ---------------- GIF ----------------
    try:
        gif = Image.open(paths.assistant_gif)
        frames = []
        w, h = 250, 180
        if hasattr(gif, "n_frames"):
            for i in range(gif.n_frames):
                gif.seek(i)
                frame = gif.copy().resize((w, h), Image.LANCZOS)
                frames.append(ImageTk.PhotoImage(frame))
        else:
            frames.append(ImageTk.PhotoImage(gif.resize((w, h), Image.LANCZOS)))

        image_label = tk.Label(root, bg=BG_COLOR)
        image_label.pack(pady=(10, 5))

        def animate(idx=0):
            frame = frames[idx]
            image_label.config(image=frame)
            if len(frames) > 1:
                root.after(100, animate, (idx + 1) % len(frames))

        animate()
    except Exception as e:
        print(f"GIF error: {e}")
        image_label = tk.Label(
            root, text="[GIF ERROR]", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 12)
        )
        image_label.pack(pady=(10, 5))

    # ---------------- STATUS LABEL (auto-resize window) ----------------
    status_label = tk.Label(
        root,
        text="Arjun is inactive.",
        fg=ACCENT_COLOR,
        bg=BG_COLOR,
        font=("Segoe UI", 11, "italic"),
        wraplength=260,
        justify="center",
    )
    status_label.pack(pady=(5, 10), padx=10)

    def set_status(msg: str):
        """Update status text and adjust window height so full text is visible."""
        nonlocal base_status_height

        status_label.config(text=msg)
        root.update_idletasks()

        # Measure required label height
        needed = status_label.winfo_reqheight()

        # On first call, record baseline height (for short text)
        if base_status_height is None:
            base_status_height = needed

        extra = max(0, needed - base_status_height)
        # Cap extra height so window doesn't go crazy tall
        extra = min(extra, 220)

        new_height = WINDOW_BASE_HEIGHT + extra
        root.geometry(f"{WINDOW_WIDTH}x{new_height}")

    # initialize baseline
    set_status("Arjun is inactive.")

    # ---------------- MODE LABEL ----------------
    mode_label = tk.Label(
        root,
        text="Mode: Friendly",
        fg=TEXT_COLOR,
        bg=BG_COLOR,
        font=("Segoe UI", 10, "italic"),
    )
    mode_label.pack(pady=(0, 10))

    # ---------------- BUTTONS ----------------
    def on_button_enter(event, button, color):
        button.config(bg=color)

    def on_button_leave(event, button, color):
        button.config(bg=color)

    button_frame = tk.Frame(root, bg=BG_COLOR)
    button_frame.pack(fill="x", padx=15, pady=(0, 15))
    for col in (0, 1, 2):
        button_frame.columnconfigure(col, weight=1)

    assistant = JarvisAssistant(gui_queue, update_gui_status)

    def start_thread():
        start_button.config(state="disabled")
        t = threading.Thread(target=assistant.run, daemon=True)
        t.start()

    def gui_toggle_sleep():
        assistant.toggle_sleep()
        set_status("Toggling sleep state...")

    start_button = tk.Button(
        button_frame,
        text="Start",
        command=start_thread,
        bg="#333333",
        fg=TEXT_COLOR,
        font=("Segoe UI", 12, "bold"),
        relief="flat",
        borderwidth=0,
        pady=5,
    )
    start_button.grid(row=0, column=0, sticky="ew", padx=4)
    start_button.bind(
        "<Enter>", lambda e: on_button_enter(e, start_button, "#444444")
    )
    start_button.bind(
        "<Leave>", lambda e: on_button_leave(e, start_button, "#333333")
    )

    sleep_button = tk.Button(
        button_frame,
        text="Sleep",
        command=gui_toggle_sleep,
        bg="#555555",
        fg=TEXT_COLOR,
        font=("Segoe UI", 12),
        relief="flat",
        borderwidth=0,
        pady=5,
    )
    sleep_button.grid(row=0, column=1, sticky="ew", padx=4)
    sleep_button.bind(
        "<Enter>", lambda e: on_button_enter(e, sleep_button, "#666666")
    )
    sleep_button.bind(
        "<Leave>", lambda e: on_button_leave(e, sleep_button, "#555555")
    )

    quit_button = tk.Button(
        button_frame,
        text="Quit",
        command=root.destroy,
        bg=QUIT_COLOR,
        fg=TEXT_COLOR,
        font=("Segoe UI", 12),
        relief="flat",
        borderwidth=0,
        pady=5,
    )
    quit_button.grid(row=0, column=2, sticky="ew", padx=4)
    quit_button.bind(
        "<Enter>", lambda e: on_button_enter(e, quit_button, QUIT_HOVER)
    )
    quit_button.bind(
        "<Leave>", lambda e: on_button_leave(e, quit_button, QUIT_COLOR)
    )

    # ---------------- DRAG WINDOW BY GIF ----------------
    def move_window(event):
        root.geometry(
            f"+{event.x_root - root.winfo_width() // 2}+{event.y_root - 20}"
        )

    image_label.bind("<B1-Motion>", move_window)

    # ---------------- QUEUE HANDLER ----------------
    def process_gui_queue():
        nonlocal current_wake_name

        try:
            msg = gui_queue.get_nowait()

            if msg == "QUIT":
                root.destroy()

            elif msg == "STATE:SLEEPING":
                text = f"Sleeping... (Say 'Hey {current_wake_name}' to wake)"
                set_status(text)
                sleep_button.config(text="Wake Up", bg="#006400")

            elif msg == "STATE:AWAKE":
                text = "Arjun is online and ready."
                set_status(text)
                sleep_button.config(text="Sleep", bg="#555555")

            elif msg.startswith("MODE:"):
                if "FRIENDLY" in msg:
                    mode_label.config(text="Mode: Friendly")
                elif "JARVIS" in msg:
                    mode_label.config(text="Mode: Jarvis-style")

            # update wake word name
            elif msg.startswith("WAKEWORD:"):
                new_name = msg.split(":", 1)[1].strip() or "Arjun"
                current_wake_name = new_name
                # if currently sleeping, refresh text
                if "Sleeping..." in status_label.cget("text"):
                    text = f"Sleeping... (Say 'Hey {current_wake_name}' to wake)"
                    set_status(text)

            else:
                set_status(msg)

        except queue.Empty:
            pass

        root.after(100, process_gui_queue)

    root.after(100, process_gui_queue)
    root.mainloop()
