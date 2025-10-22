FROM cadquery/cadquery:latest
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"
WORKDIR /app
COPY app /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
