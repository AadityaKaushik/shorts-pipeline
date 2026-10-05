FROM manimcommunity/manim:stable

USER root
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

WORKDIR /app
COPY app.py shorts_base.py ./

USER 1000:1000
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]