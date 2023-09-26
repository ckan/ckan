FROM python:3.9
LABEL maintainer="maximiliano.pizarro.5@gmail.com"
ADD . /usr/lib/
WORKDIR /usr/lib/

RUN pip install -r requirements.txt
RUN python setup.py install

EXPOSE 5000

CMD ["ckan","-c","/usr/lib/who.ini", "run", "--host", "0.0.0.0"]