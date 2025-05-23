from flask import Flask, request, render_template, send_file, redirect, url_for
import os
import uuid
import asyncio
from llm_aided_ocr import convert_pdf_to_images, ocr_image, process_document, remove_corrected_text_header

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        reformat = request.form.get("reformat_as_markdown") == "on"
        suppress_headers = request.form.get("suppress_headers") == "on"

        if file and file.filename.endswith(".pdf"):
            uid = str(uuid.uuid4())[:8]
            filename = f"{uid}_{file.filename}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            final_text, raw_text = loop.run_until_complete(run_ocr_pipeline(file_path, reformat, suppress_headers))

            corrected_path = os.path.join(OUTPUT_FOLDER, f"{filename}_corrected.md" if reformat else f"{filename}_corrected.txt")
            raw_path = os.path.join(OUTPUT_FOLDER, f"{filename}_raw.txt")

            with open(corrected_path, "w") as f:
                f.write(final_text)
            with open(raw_path, "w") as f:
                f.write(raw_text)

            return render_template("index.html", corrected_file=corrected_path, raw_file=raw_path)

    return render_template("index.html")

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_file(filename, as_attachment=True)

async def run_ocr_pipeline(pdf_path, reformat, suppress):
    images = convert_pdf_to_images(pdf_path)
    raw_text_list = [ocr_image(img) for img in images]
    raw_text = "\n".join(raw_text_list)
    corrected = await process_document(raw_text_list, reformat_as_markdown=reformat, suppress_headers_and_page_numbers=suppress)
    return remove_corrected_text_header(corrected), raw_text

if __name__ == "__main__":
    app.run(debug=True)
