from PIL import Image, ImageDraw, ImageFont
import os

# List of (filename, label) pairs for all truck records
images = [
    ("fordf350xl_white_123.jpg", "2024 FORD F-350 XL WHITE 123"),
    ("chevg2500_silver_789.jpg", "2023 CHEV G2500 SILVER 789"),
    ("ram5500_dump_456.jpg", "2022 RAM 5500 DUMP 456"),
    ("hino338_box_001.jpg", "2024 HINO 338 BOX 001"),
    ("isuzunprhd_red_555.jpg", "2019 ISUZU NPR-HD RED 555"),
]

output_dir = "assets/images"
os.makedirs(output_dir, exist_ok=True)

for filename, label in images:
    img = Image.new("RGB", (400, 200), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    try:
        # Try to load a TTF font for better appearance, fallback to default
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    text_w, text_h = draw.textsize(label, font=font)
    text_x = (img.width - text_w) // 2
    text_y = (img.height - text_h) // 2
    draw.text((text_x, text_y), label, font=font, fill=(30,30,30))
    img.save(os.path.join(output_dir, filename))
print(f"Dummy images saved to: {output_dir}")