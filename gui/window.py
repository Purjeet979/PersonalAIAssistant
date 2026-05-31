import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import queue
import pystray
from jarvis.assistant import JarvisAssistant
from jarvis.paths import paths

# Set CustomTkinter Appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def run_app():
    WINDOW_WIDTH = 260
    WINDOW_BASE_HEIGHT = 380

    root = ctk.CTk()
    root.title("Arjun")
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_BASE_HEIGHT}")

    current_wake_name = "Arjun"
    base_status_height = None

    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 1.0)

    # Trick for borderless rounded corners in Windows (use magenta so it doesn't match GIF black pixels)
    TRANSPARENT_COLOR = "#FF00FF"
    root.configure(bg=TRANSPARENT_COLOR, fg_color=TRANSPARENT_COLOR)
    root.attributes("-transparentcolor", TRANSPARENT_COLOR)

    # Main container with broader rounded corners
    main_frame = ctk.CTkFrame(
        root, 
        fg_color="#000000", 
        corner_radius=30, 
        bg_color=TRANSPARENT_COLOR
    )
    main_frame.pack(fill="both", expand=True)

    gui_queue = queue.Queue()

    def update_gui_status(text):
        gui_queue.put(text)

    try:
        gif = Image.open(paths.assistant_gif)
        frames = []
        # Reduced GIF size to fit smaller window
        w, h = 200, 140
        
        orig_w, orig_h = gif.size
        left = int(orig_w * 0.20)
        top = int(orig_h * 0.20)
        right = int(orig_w * 0.80)
        bottom = int(orig_h * 0.80)
        
        if hasattr(gif, "n_frames"):
            for i in range(gif.n_frames):
                gif.seek(i)
                # Convert to RGBA to fix palette resizing glitches
                frame_rgba = gif.copy().convert("RGBA")
                cropped = frame_rgba.crop((left, top, right, bottom))
                resized = cropped.resize((w, h), Image.LANCZOS)
                
                # Composite over black background to prevent Tkinter alpha issues
                bg = Image.new("RGBA", resized.size, (0, 0, 0, 255))
                frame_final = Image.alpha_composite(bg, resized)
                frames.append(ImageTk.PhotoImage(frame_final))
        else:
            frame_rgba = gif.copy().convert("RGBA")
            cropped = frame_rgba.crop((left, top, right, bottom))
            resized = cropped.resize((w, h), Image.LANCZOS)
            bg = Image.new("RGBA", resized.size, (0, 0, 0, 255))
            frame_final = Image.alpha_composite(bg, resized)
            frames.append(ImageTk.PhotoImage(frame_final))

        image_label = tk.Label(main_frame, bg="#000000", borderwidth=0)
        image_label.pack(pady=(15, 0))

        def animate(idx=0):
            frame = frames[idx]
            image_label.config(image=frame)
            if len(frames) > 1:
                root.after(100, animate, (idx + 1) % len(frames))

        animate()
    except Exception as e:
        print(f"GIF error: {e}")
        image_label = ctk.CTkLabel(
            main_frame, text="[GIF ERROR]", font=("Segoe UI", 12), text_color="#FFFFFF"
        )
        image_label.pack(pady=(10, 0))

    status_label = ctk.CTkLabel(
        main_frame,
        text="Arjun is inactive.",
        text_color="#A0DDEE",
        font=("Segoe UI", 12, "italic"),
        wraplength=230,
        justify="center",
    )
    status_label.pack(pady=(10, 5), padx=10)

    def set_status(msg: str):
        nonlocal base_status_height

        status_label.configure(text=msg)
        root.update_idletasks()

        needed = status_label.winfo_reqheight()

        if base_status_height is None:
            base_status_height = needed

        extra = max(0, needed - base_status_height)
        extra = min(extra, 200)

        new_height = WINDOW_BASE_HEIGHT + extra
        root.geometry(f"{WINDOW_WIDTH}x{new_height}")

    set_status("Arjun is inactive.")

    mode_label = ctk.CTkLabel(
        main_frame,
        text="Mode: Friendly",
        font=("Segoe UI", 11, "italic"),
        text_color="#FFFFFF"
    )
    mode_label.pack(pady=(0, 10))

    action_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    action_frame.pack(fill="x", padx=20, pady=(0, 10))

    assistant = JarvisAssistant(gui_queue, update_gui_status)

    def start_thread():
        t = threading.Thread(target=assistant.run, daemon=True)
        t.start()

    def gui_toggle_sleep():
        assistant.toggle_sleep()
        set_status("Toggling sleep state...")

    def hide_to_tray():
        root.withdraw()
        
        try:
            icon_image = Image.open(paths.assistant_gif).copy().resize((64, 64), Image.LANCZOS)
        except Exception:
            icon_image = Image.new('RGB', (64, 64), color=(0, 255, 0))
            
        def on_show_clicked(icon_obj, item):
            icon_obj.stop()
            root.after(0, root.deiconify)

        def on_quit_clicked(icon_obj, item):
            icon_obj.stop()
            root.after(0, root.destroy)
            
        menu = pystray.Menu(
            pystray.MenuItem('Show', on_show_clicked, default=True),
            pystray.MenuItem('Quit', on_quit_clicked)
        )
        
        icon = pystray.Icon("Arjun", icon_image, "Arjun AI", menu)
        threading.Thread(target=icon.run, daemon=True).start()

    action_frame.columnconfigure(0, weight=1)
    action_frame.columnconfigure(1, weight=1)

    def on_start_click():
        start_btn.configure(state="disabled", text="Running...")
        start_thread()

    def on_end_click():
        root.destroy()

    def gui_toggle_sleep():
        assistant.toggle_sleep()
        set_status("Toggling sleep state...")

    def on_option_select(choice):
        if choice == "Sleep / Wake":
            gui_toggle_sleep()
        elif choice == "Hide (To Tray)":
            hide_to_tray()
        options_menu.set("More Options...")

    start_btn = ctk.CTkButton(
        action_frame,
        text="Start AI",
        command=on_start_click,
        font=("Segoe UI", 12, "bold"),
        fg_color="#1f538d",
        hover_color="#14375e",
        height=30
    )
    start_btn.grid(row=0, column=0, sticky="ew", padx=3, pady=(0, 5))

    end_btn = ctk.CTkButton(
        action_frame,
        text="Quit",
        command=on_end_click,
        font=("Segoe UI", 12, "bold"),
        fg_color="#8c1b1b",
        hover_color="#a82222",
        height=30
    )
    end_btn.grid(row=0, column=1, sticky="ew", padx=3, pady=(0, 5))

    options_menu = ctk.CTkOptionMenu(
        action_frame,
        values=["Sleep / Wake", "Hide (To Tray)"],
        command=on_option_select,
        font=("Segoe UI", 12, "bold"),
        fg_color="#454545",
        button_color="#333333",
        button_hover_color="#555555",
        height=30
    )
    options_menu.set("More Options...")
    options_menu.grid(row=1, column=0, columnspan=2, sticky="ew", padx=3)

    def gui_good_feedback():
        if assistant.save_last_interaction("good"):
            set_status("Feedback: Saved as 👍 Good response!")
        else:
            set_status("No recent response to rate.")

    def gui_bad_feedback():
        if assistant.save_last_interaction("bad"):
            set_status("Feedback: Saved as 👎 Bad response.")
        else:
            set_status("No recent response to rate.")

    feedback_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    feedback_frame.pack(fill="x", padx=15, pady=(0, 15))
    feedback_frame.columnconfigure(0, weight=1)
    feedback_frame.columnconfigure(1, weight=1)

    good_btn = ctk.CTkButton(
        feedback_frame,
        text="👍 Good",
        command=gui_good_feedback,
        font=("Segoe UI", 12),
        fg_color="#2E7D32",
        hover_color="#388E3C",
        height=30
    )
    good_btn.grid(row=0, column=0, sticky="ew", padx=3)

    bad_btn = ctk.CTkButton(
        feedback_frame,
        text="👎 Bad",
        command=gui_bad_feedback,
        font=("Segoe UI", 12),
        fg_color="#8c1b1b",
        hover_color="#a82222",
        height=30
    )
    bad_btn.grid(row=0, column=1, sticky="ew", padx=3)

    def move_window(event):
        root.geometry(
            f"+{event.x_root - root.winfo_width() // 2}+{event.y_root - 20}"
        )

    # Bind dragging to the main frame and GIF so user can move it anywhere
    image_label.bind("<B1-Motion>", move_window)
    main_frame.bind("<B1-Motion>", move_window)

    def process_gui_queue():
        nonlocal current_wake_name

        try:
            msg = gui_queue.get_nowait()

            if msg == "QUIT":
                root.destroy()
                return

            elif msg == "STATE:SLEEPING":
                text = f"Sleeping... (Say 'Hey {current_wake_name}' to wake)"
                set_status(text)

            elif msg == "STATE:AWAKE":
                text = "Arjun is online and ready."
                set_status(text)

            elif msg.startswith("MODE:"):
                if "FRIENDLY" in msg:
                    mode_label.configure(text="Mode: Friendly")
                elif "JARVIS" in msg:
                    mode_label.configure(text="Mode: Jarvis-style")

            elif msg.startswith("WAKEWORD:"):
                new_name = msg.split(":", 1)[1].strip() or "Arjun"
                current_wake_name = new_name

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
