from manga_ocr import MangaOcr

def warmup():
    print("Pre-downloading manga-ocr model...")
    # MangaOcr() downloads the default model (kha-white/manga-ocr-base)
    _ = MangaOcr()
    print("manga-ocr model downloaded successfully.")

if __name__ == "__main__":
    warmup()
