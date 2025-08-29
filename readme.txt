commands and general info:
    cd /home/chasidustv/SimpleVideoLib
    git pull
    nano .env
    journalctl -u chasidustv -f
    systemctl start chasidustv
    systemctl status chasidustv
    systemctl restart chasidustv
    systemctl stop chasidustv
    nginx -t # to test
    nginx -s restart

update:
    on local:
        commit
        sync/push

    then on vds: (option 1)
        su chasidustv
        cd ~/SimpleVideoLib
        git pull
        exit
        systemctl restart chasidustv

    then on vds: (option 2)
        cd /home/chasidustv/SimpleVideoLib
        git pull
        optionally:
            chown  chasidustv:chasidustv *
            chown  chasidustv:chasidustv .*
        systemctl restart chasidustv

services setup:
    [Unit]
    Description=ChasidusTV Gunicorn Server
    After=network.target

    [Service]
    User=chasidustv
    WorkingDirectory=/home/chasidustv/SimpleVideoLib
    ExecStart=/home/chasidustv/python-portable/bin/python3.12 -u -m gunicorn -b 127.0.0.1:9000 "app:create_app()"
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target