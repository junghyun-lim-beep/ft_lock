#!/usr/bin/env python3
"""
Create a beautiful gradient background for the lock screen
"""

from PIL import Image, ImageDraw
import os

def create_gradient_background(width=1920, height=1080):
    """Create a beautiful gradient background image"""
    # Create a new image with gradient
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    # Create a diagonal gradient from deep blue to purple
    for y in range(height):
        for x in range(width):
            # Calculate distance from top-left corner
            distance = ((x**2 + y**2) ** 0.5) / ((width**2 + height**2) ** 0.5)
            
            # Colors: deep blue to purple to dark purple
            if distance < 0.5:
                # Interpolate between deep blue and purple
                r = int(25 + (85 * distance * 2))
                g = int(25 + (25 * distance * 2))
                b = int(112 + (26 * distance * 2))
            else:
                # Interpolate between purple and dark purple
                r = int(110 - (40 * (distance - 0.5) * 2))
                g = int(50 - (30 * (distance - 0.5) * 2))
                b = int(138 - (38 * (distance - 0.5) * 2))
            
            draw.point((x, y), (r, g, b))
    
    # Add some subtle noise/texture
    for _ in range(1000):
        import random
        x = random.randint(0, width-1)
        y = random.randint(0, height-1)
        brightness = random.randint(-10, 10)
        current_color = image.getpixel((x, y))
        new_color = tuple(max(0, min(255, c + brightness)) for c in current_color)
        draw.point((x, y), new_color)
    
    return image

def main():
    # Create the images directory if it doesn't exist
    os.makedirs('images', exist_ok=True)
    
    # Create the background image
    print("Creating beautiful gradient background...")
    bg_image = create_gradient_background()
    
    # Save the background image
    bg_path = 'images/lock_background.png'
    bg_image.save(bg_path)
    print(f"Background saved to {bg_path}")

if __name__ == "__main__":
    main()
