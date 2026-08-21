# Reproducible environment for generating the CV PDF from index.html.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate_cv.py .

# The caller is expected to bind-mount the repository at /workspace
# (containing index.html) and an output directory at /output.
ENTRYPOINT ["python", "generate_cv.py"]
CMD ["--input", "/workspace/index.html", "--output", "/output/Pieter_Joost_van_de_Sande_CV.pdf"]
