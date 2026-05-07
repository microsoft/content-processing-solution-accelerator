#!/bin/sh

# Ensure APP_BACKEND_API_URL has a safe default so nginx can always start.
# When not set, the /api/ proxy_pass will point to a non-routable placeholder
# and return 502, which is acceptable — the direct API path still works.
export APP_BACKEND_API_URL="${APP_BACKEND_API_URL:-http://localhost:8080}"

for i in $(env | grep ^APP_)
do
    key=$(echo $i | cut -d '=' -f 1)
    value=$(echo $i | cut -d '=' -f 2-)
    echo $key=$value
    # Use sed to replace only the exact matches of the key
    find /usr/share/nginx/html -type f -exec sed -i "s|\b${key}\b|${value}|g" '{}' +
    sed -i "s|\b${key}\b|${value}|g" /etc/nginx/nginx.conf
done
echo 'done'