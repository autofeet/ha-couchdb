FROM couchdb:3.5.3

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /opt/couchdb/etc/local.d \
    && ln -s /data/local.d /opt/couchdb/etc/local.d

COPY configure.py /usr/local/bin/ha-couchdb.py
ENTRYPOINT ["tini", "--", "python3", "/usr/local/bin/ha-couchdb.py"]
CMD ["/opt/couchdb/bin/couchdb"]
