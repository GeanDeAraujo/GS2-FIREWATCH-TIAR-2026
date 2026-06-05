FROM public.ecr.aws/lambda/python:3.11

# libgomp is needed by ultralytics/torch; opencv-python-headless handles the rest
RUN yum install -y libgomp mesa-libGL && yum clean all

COPY requirements.txt .
# Install CPU-only torch first to prevent ultralytics from pulling CUDA (~2.5 GB)
RUN pip install --upgrade pip && \
    pip install --prefer-binary \
        torch==2.6.0 torchvision==0.21.0 \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy handler code directly to task root so imports (config, services.*) resolve correctly
COPY processor/ ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
