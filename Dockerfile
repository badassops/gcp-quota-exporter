
# -- setup base -- #
FROM python:3.7-alpine
ARG PORT

# -- setup global profiles file -- #
WORKDIR /etc
COPY profile/profile profile
RUN	echo 'UTC' > timezone

# -- install package -- #
RUN apk -q update
RUN apk add --no-cache tzdata \
	bash \
	curl \
	htop \
	py3-pip \
	vim \
	bind-tools

# -- setup Application's user -- #
WORKDIR /app
RUN adduser -D -u 25000 -g app -h /app app && \
	chown -Rh app:app /app

# -- allow connection in from given PORT argument -- #
CMD echo "Port $port being exposed"
EXPOSE $PORT

# -- install application and required components -- #
RUN pip3 --disable-pip-version-check install --no-cache-dir pipenv
COPY Pipfile* ./
RUN pipenv install --system --deploy
COPY exporter.py .
COPY setup.cfg .
RUN chown -Rh app:app /app
RUN chmod 755 exporter.py
RUN chmod 0444 setup.cfg Pipfile*

# -- run the application -- #
USER app
CMD [ "./exporter.py" ]
