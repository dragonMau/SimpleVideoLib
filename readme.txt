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

    then vds:
        ssh chasidustv
        cd ~/SimpleVideoLib
        git pull
        systemctl restart chasidustv
        # password of chasidustv user
        journalctl -u chasidustv -f

services setup:
    [Unit]
    Description=ChasidusTV Gunicorn Server
    After=network.target

    [Service]
    User=chasidustv
    WorkingDirectory=/home/chasidustv/SimpleVideoLib
    ExecStart=/home/chasidustv/python-portable/bin/python3.12 -u -m gunicorn -w 2 -b 127.0.0.1:9000 "app:create_app()"
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target