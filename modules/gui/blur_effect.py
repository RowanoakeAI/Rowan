import customtkinter as ctk
from PIL import Image, ImageFilter

class BlurFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        corner_radius: int = 10,
        blur_intensity: int = 10,
        transparency: float = 0.8,
        **kwargs
    ):
        super().__init__(master, corner_radius=corner_radius, **kwargs)
        
        # Store parameters
        self.blur_intensity = blur_intensity
        self.transparency = max(0.0, min(1.0, transparency))
        
        # Configure transparent background
        self.configure(
            fg_color=self._apply_transparency(self._fg_color),
            border_width=1,
            border_color="gray20"
        )
        
        # Create label for blur effect
        self.blur_label = ctk.CTkLabel(self, text="")
        self.blur_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Initialize blur image
        self._blur_image = None
        
        # Bind redraw events
        self.bind("<Configure>", self._on_resize)
        
        # Initial draw
        self._draw_blur()
        
    def _apply_transparency(self, color):
        """Applies transparency to color value"""
        if isinstance(color, tuple):
            # Handle RGB/RGBA tuples
            return tuple(int(c * self.transparency) for c in color[:3]) + (
                int(255 * self.transparency),)
        elif isinstance(color, str) and color.startswith("#"):
            # Convert hex to RGBA
            r = int(color[1:3], 16)
            g = int(color[3:5], 16) 
            b = int(color[5:7], 16)
            a = int(255 * self.transparency)
            return f'#{r:02x}{g:02x}{b:02x}{a:02x}'
        return color
        
    def _draw_blur(self):
        """Draws the blurred background effect"""
        try:
            # Get widget dimensions
            width = self.winfo_width()
            height = self.winfo_height()
            
            if width <= 1 or height <= 1:
                return  # Skip invalid dimensions
                
            # Create base transparent image
            base = Image.new("RGBA", (width, height), (0,0,0,0))
            
            # Create semi-transparent overlay
            overlay = Image.new("RGBA", (width, height), 
                              (20, 20, 20, int(100 * self.transparency)))
            
            # Apply gaussian blur
            blurred = overlay.filter(ImageFilter.GaussianBlur(radius=self.blur_intensity))
            
            # Composite images
            final = Image.alpha_composite(base, blurred)
            
            # Convert to CTkImage and store reference
            self._blur_image = ctk.CTkImage(
                light_image=final,
                dark_image=final,
                size=(width, height)
            )
            
            # Update background via label
            self.blur_label.configure(image=self._blur_image)
            
        except Exception as e:
            print(f"Error drawing blur: {e}")
            
    def _on_resize(self, event):
        """Handle resize events"""
        # Use after() to avoid rapid redraws
        self.after(10, self._draw_blur)
        
    def configure(self, **kwargs):
        """Override configure to handle transparency changes"""
        if "transparency" in kwargs:
            self.transparency = max(0.0, min(1.0, kwargs.pop("transparency")))
            self._draw_blur()
        super().configure(**kwargs)