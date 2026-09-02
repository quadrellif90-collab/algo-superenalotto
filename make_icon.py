"""Genera icona SuperEnalotto (verde, pallina + S) e la salva come .ico."""
from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# cerchio verde (stacco rispetto al rosso superenalotto)
green = (26, 143, 60, 255)
green_dk = (15, 107, 44, 255)
d.ellipse([16, 16, SIZE - 16, SIZE - 16], fill=green, outline=green_dk, width=6)

# lettera S bianca al centro
try:
            font = ImageFont.truetype("arial.ttf", 150)
        except OSError:
            font = ImageFont.load_default(150)
txt = "S"
bbox = d.textbbox((0, 0), txt, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
d.text(((SIZE - tw) / 2 - bbox[0], (SIZE - th) / 2 - bbox[1]), txt, fill=(255, 255, 255, 255), font=font)

# salva PNG
png = "icon.png"
img.save(png)

# salva ICO multi-risoluzione
img.save("icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon.png + icon.ico creati")
