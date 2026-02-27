# FROM python:3.11

# WORKDIR /app

# # Copy requirements first
# COPY backend/requirements.txt ./requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy backend code
# COPY backend/ ./backend

# # Copy frontend folder
# COPY frontend/ ./frontend

# # Set working directory to backend
# WORKDIR /app/backend

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]  


FROM python:3.11

WORKDIR /app

COPY backend/ ./backend
COPY frontend/ ./frontend

WORKDIR /app/backend

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]