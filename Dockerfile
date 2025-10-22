FROM cadquery/cadquery:latest

# NEW: Add the local bin directory to the system's PATH
ENV PATH="/home/cq/.local/bin:${PATH}"

# Install Python dependencies
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

# Set working directory and copy app files
WORKDIR /app
COPY app/ .

# Expose port and run the server
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
