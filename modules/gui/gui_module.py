import customtkinter as ctk
from tkinter import ttk
import sv_ttk  # For modern Fluent design
from PIL import Image, ImageTk
import os
from typing import Optional
from datetime import datetime
import threading
from pathlib import Path

# Add forward reference hint for RowanAssistant to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.rowan_assistant import RowanAssistant

from core.personal_memory import InteractionSource

# Set theme and color scheme
ctk.set_appearance_mode("dark") 
ctk.set_default_color_theme("blue")

class ModernMessage(ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        message = kwargs.pop('message', '')
        is_user = kwargs.pop('is_user', False)
        super().__init__(*args, **kwargs)
        
        self.configure(fg_color='#2662de' if is_user else '#333333')
        
        self.message = ctk.CTkLabel(
            self,
            text=message,
            font=('Inter', 14),
            wraplength=400,
            justify='left'
        )
        self.message.pack(padx=15, pady=10)

class RowanGUI(ctk.CTk):
    def __init__(self, rowan_assistant: Optional['RowanAssistant'] = None):
        super().__init__()
        
        # Set window icons - both methods needed for different platforms
        icon_path = Path(__file__).parent.parent.parent / "assets" / "rowan.png"
        if icon_path.exists():
            # For Windows taskbar
            self.iconbitmap(default=str(icon_path.with_suffix('.ico')))
            # For window title bar
            icon_image = ImageTk.PhotoImage(Image.open(icon_path))
            self.iconphoto(True, icon_image)
            # Keep reference to prevent garbage collection
            self._icon_image = icon_image
        
        # Apply Fluent design
        sv_ttk.set_theme("dark")
        
        self.rowan = rowan_assistant
        self.processing = False
        
        # Configure window
        self.title("Rowan")
        self.geometry("1200x800")
        self.configure(fg_color="#1a1a1a")
        
        # Main UI setup
        self._setup_main_frame()
        self._setup_sidebar()
        self._setup_chat_area()
        self._setup_input_area()
        
        # Initialize animations
        self.animations = {
            'typing': self._create_typing_animation(),
            'message_appear': self._create_message_animation()
        }

    def _setup_main_frame(self):
        """Setup main frame with transparency"""
        self.main_frame = ctk.CTkFrame(
            self,
            corner_radius=20,
            fg_color=("#ffffff", "#1e1e1e")
        )
        self.main_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Configure main_frame grid with explicit minimum size
        self.main_frame.grid_rowconfigure(0, weight=1, minsize=400)  # Chat container
        self.main_frame.grid_rowconfigure(1, weight=0)  # Input area
        self.main_frame.grid_columnconfigure(0, weight=1)

    def _setup_sidebar(self):
        """Setup sidebar with clear chat button and status label"""
        self.sidebar = ctk.CTkFrame(
            self,
            width=250,
            corner_radius=0,
            fg_color="#161616"
        )
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        
        # Add clear chat button to sidebar
        self.clear_button = ctk.CTkButton(
            self.sidebar,
            text="Clear Chat",
            command=self._clear_chat,
            fg_color="#2662de",
            hover_color="#1e4fc2"
        )
        self.clear_button.pack(padx=20, pady=20)
        
        # Add status variable
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            textvariable=self.status_var,
            text_color="#909090"
        )
        self.status_label.pack(side="bottom", pady=10)

    def _setup_chat_area(self):
        """Setup chat container and display"""
        self.chat_container = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color="transparent",
            scrollbar_button_color="#2662de",
            scrollbar_button_hover_color="#1e4fc2"
        )
        self.chat_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        
        # Force chat container expansion
        self.chat_container.grid_columnconfigure(0, weight=1)
        
        # Configure chat display with explicit height
        self.chat_display = ctk.CTkTextbox(
            self.chat_container,
            fg_color="transparent", 
            font=("Inter", 14),
            wrap="word",
            height=600  # Increased height
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.chat_display.configure(state="disabled")
        
        # Configure tags on the underlying Tkinter Text widget
        self.chat_display._textbox.tag_configure("user", foreground="#2662de")
        self.chat_display._textbox.tag_configure("assistant", foreground="#909090")
        self.chat_display._textbox.tag_configure("timestamp", foreground="#666666")

    def _setup_input_area(self):
        """Setup input area with send button"""
        self.input_area = ctk.CTkFrame(
            self.main_frame,
            height=100,
            fg_color="#212121"
        )
        self.input_area.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        # Message entry
        self.msg_entry = ctk.CTkEntry(
            self.input_area,
            placeholder_text="Type your message...",
            font=("Inter", 14),
            height=40
        )
        self.msg_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")
        self.msg_entry.bind("<Return>", self._send_message)
        
        # Configure grid weights
        self.input_area.grid_columnconfigure(0, weight=1)
        self.input_area.grid_columnconfigure(1, weight=0)
        
        try:
            # Try to load send icon
            icon_path = os.path.join(os.path.dirname(__file__), "icons", "send.png")
            if os.path.exists(icon_path):
                send_icon = ctk.CTkImage(Image.open(icon_path))
                self.send_button = ctk.CTkButton(
                    self.input_area,
                    text="",
                    image=send_icon,
                    width=40,
                    height=40,
                    corner_radius=20,
                    fg_color="#2662de",
                    hover_color="#1e4fc2",
                    command=self._send_message
                )
            else:
                raise FileNotFoundError("Send icon not found")
                
        except Exception as e:
            # Fallback to text button if image loading fails
            self.send_button = ctk.CTkButton(
                self.input_area,
                text="Send",
                width=70,
                height=40,
                corner_radius=20,
                fg_color="#2662de",
                hover_color="#1e4fc2",
                command=self._send_message
            )
            
        self.send_button.grid(row=0, column=1, padx=(5, 10), pady=10)

    def _create_typing_animation(self):
        """Creates a simple typing indicator animation"""
        def animate():
            if not self.processing:
                self.typing_indicator.grid_remove()
                return
            
            current_text = self.typing_indicator.cget("text")
            if current_text.count(".") >= 3:
                self.typing_indicator.configure(text="Assistant is typing")
            else:
                self.typing_indicator.configure(text=current_text + ".")
            
            self.typing_indicator.grid()
            self.after(500, animate)
        
        return animate

    def _create_message_animation(self):
        """Creates a smooth fade-in animation for new messages"""
        def animate(widget, alpha=0.0):
            if alpha < 1.0:
                widget.configure(fg_color=f'#{int(alpha * 255):02x}{int(alpha * 255):02x}{int(alpha * 255):02x}')
                self.after(50, lambda: animate(widget, alpha + 0.1))
        
        return animate

    def _send_message(self, event=None):
        if self.processing:
            return

        message = self.msg_entry.get().strip()
        if not message:
            return

        self.msg_entry.delete(0, len(message))
        self._update_chat("You", message, "user")
        
        self.processing = True
        self.status_var.set("Processing...")
        self.send_button.configure(state="disabled")
        threading.Thread(target=self._process_message, args=(message,), daemon=True).start()

    def _process_message(self, message: str):
        try:
            if not self.rowan:
                response = "Error: Rowan assistant not initialized"
            else:
                response = self.rowan.chat(message, source=InteractionSource.GUI)

            self.after(0, self._update_chat, "Assistant", response, "assistant")
            self.after(0, self.status_var.set, "Ready")
            self.after(0, self.send_button.configure, {"state": "normal"})

        finally:
            self.processing = False

    def _update_chat(self, sender: str, message: str, tag: str):
        self.chat_display.configure(state="normal")
        
        timestamp = datetime.now().strftime("%H:%M")
        
        self.chat_display.insert("end", f"\n{timestamp} ", "timestamp")
        self.chat_display.insert("end", f"{sender}:\n", tag)
        self.chat_display.insert("end", f"{message}\n")
        
        # Force scroll to bottom and update the widget
        self.chat_display.see("end")
        self.chat_display.update_idletasks()
        self.chat_display.configure(state="disabled")
        
        # Ensure parent containers are scrolled too
        self.chat_container.update_idletasks()
        self.chat_container._parent_canvas.yview_moveto(1.0)

    def _clear_chat(self):
        if not self._show_confirmation():
            return
            
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.status_var.set("Chat cleared")

    def _show_confirmation(self) -> bool:
        dialog = ctk.CTkInputDialog(
            text="Type 'yes' to confirm clearing chat history",
            title="Clear Chat",
            fg_color="#212121",
            button_fg_color="#2662de",
            button_hover_color="#1e4fc2"
        )
        return dialog.get_input() == "yes"