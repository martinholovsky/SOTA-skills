def render_pdf(tex_path):
    subprocess.run(["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", tex_path], check=True)
