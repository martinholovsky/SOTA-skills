def render_pdf(tex_path):
    subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_path], check=True)
