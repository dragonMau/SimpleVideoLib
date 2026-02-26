# all HTTP to HTTPS
server {
    listen 80;
    server_name chasidustv.com www.chasidustv.com;
    
    return 301 https://$host$request_uri;
}

# @ to www.@
server {
    listen 443 ssl;
    server_name chasidustv.com;
    
    ssl_certificate /etc/ssl/certs/chasidustv.pem;
    ssl_certificate_key /etc/ssl/private/chasidustv.key;
    
    return 301 https://www.chasidustv.com$request_uri;
}

# admin site
server {
    listen 443 ssl;
    server_name admin.chasidustv.com;

    ssl_certificate /etc/ssl/certs/chasidustv.pem;
    ssl_certificate_key /etc/ssl/private/chasidustv.key;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# main site
server {
    listen 443 ssl;
    server_name www.chasidustv.com;
    
    ssl_certificate /etc/ssl/certs/chasidustv.pem;
    ssl_certificate_key /etc/ssl/private/chasidustv.key;
    
    resolver 1.1.1.1 8.8.8.8 valid=300s;
    resolver_timeout 5s;

    location ~ ^/thumb/(.+)$ {
        proxy_pass https://archive.org/download/$1/__ia_thumb.jpg;
        proxy_set_header Host archive.org;
        proxy_ssl_server_name on;

        proxy_buffering off;
        
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
    
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}