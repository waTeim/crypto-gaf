FROM postgres:11
USER 0
SHELL ["/bin/bash", "-c"]
ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION 12.12.0
ENV SHELL /bin/bash

RUN apt-get -y update
RUN apt-get -y install apt-utils
RUN apt-get -y install curl
RUN apt-get -y install net-tools
RUN apt-get -y install git
RUN apt-get -y install gcc
RUN apt-get -y install python3-dev
RUN apt-get -y install postgresql-server-dev-11
RUN apt-get -y install gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 \
libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 \
ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget
RUN apt-get -y install telnet
RUN apt-get -y install iputils-ping
RUN mkdir -p /usr/local/src
RUN mkdir -p /usr/local/nvm
RUN cd /usr/local/src && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 get-pip.py
RUN pip install -U psycopg2
RUN pip install -U kafka-python
RUN curl --silent -o- https://raw.githubusercontent.com/creationix/nvm/master/install.sh | bash
RUN source $NVM_DIR/nvm.sh && nvm install $NODE_VERSION && nvm alias default $NODE_VERSION && nvm use default
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH
RUN npm -g install typescript
