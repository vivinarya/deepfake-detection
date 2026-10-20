FROM public.ecr.aws/lambda/python:3.11

# Install OS libraries required by MediaPipe and OpenCV
RUN yum install -y mesa-libGL glib2 && yum clean all

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY rppg_engine.py app.py ${LAMBDA_TASK_ROOT}/

CMD [ "app.handler" ]
