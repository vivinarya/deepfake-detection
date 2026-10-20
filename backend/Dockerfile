FROM public.ecr.aws/lambda/python:3.11

# Install OS libraries required by MediaPipe, OpenCV, and any native C/C++ builds
RUN yum install -y mesa-libGL glib2 gcc gcc-c++ && yum clean all

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --only-binary :all: -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY rppg_engine.py app.py ${LAMBDA_TASK_ROOT}/

CMD [ "app.handler" ]
