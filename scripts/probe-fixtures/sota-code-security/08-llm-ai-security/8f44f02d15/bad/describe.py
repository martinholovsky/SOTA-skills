def build_prompt(image):
    ocr_text = run_ocr(image)
    return f"Summarise this scanned document:\n{ocr_text}"
