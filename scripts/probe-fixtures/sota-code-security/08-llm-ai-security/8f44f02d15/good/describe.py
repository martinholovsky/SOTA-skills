def build_prompt(image):
    ocr_text = run_ocr(image)
    return [SYSTEM, {"role": "user", "content": frame_untrusted(ocr_text, source="ocr")}]
