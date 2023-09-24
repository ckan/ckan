FROM python:3.8.5
LABEL maintainer="maximiliano.pizarro.5@gmail.com"
RUN mkdir -p /usr/lib/ckan/default
ADD . /usr/lib/
RUN python3 -m venv /usr/lib/ckan/default
RUN . /usr/lib/ckan/default/bin/activate
WORKDIR /usr/lib/
RUN python setup.py install
RUN pip install -r requirements.txt

USER ckan
EXPOSE 5000

CMD ["ckan","-c","/usr/lib/production.ini", "run", "--host", "0.0.0.0"]