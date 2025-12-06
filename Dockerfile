# Use Apify's Python base image (3.13)
FROM apify/actor-python:3.13

# Switch to non-root user
USER myuser

# -----------------------------
# Install Playwright + Chromium
# -----------------------------
RUN pip install --no-cache-dir playwright && \
    playwright install-deps && \
    playwright install chromium

# -----------------------------
# Install Python dependencies
# -----------------------------

# Copy only requirements first to leverage Docker caching
COPY --chown=myuser:myuser requirements.txt ./requirements.txt

RUN echo "Python version:" \
 && python --version \
 && echo "Pip version:" \
 && pip --version \
 && echo "Installing dependencies from requirements.txt:" \
 && pip install --no-cache-dir -r requirements.txt \
 && echo "All installed Python packages:" \
 && pip freeze

# -----------------------------
# Copy remaining source code
# -----------------------------
COPY --chown=myuser:myuser . ./

# Optional: compile Python files to verify they are valid
RUN python3 -m compileall -q src/

# -----------------------------
# ENTRYPOINT
# -----------------------------
# Option A: run module (preferred)
CMD ["python3", "-m", "src.main"]

# Option B: if your entry is plain script:
# CMD ["python3", "src/main.py"]
