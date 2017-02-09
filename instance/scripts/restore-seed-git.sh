#!/bin/bash -x

IDENTITY=${IDENTITY:-"https://identity1.citycloud.com:5000/v3"}
REGION=${REGION:-"Lon1"}

# Authentication and endpoints
AUTH_FILE="/home/core/.config/seed/auth.json"
ENDPOINT_FILE="/home/core/.config/seed/endpoints.json"

# Object store items
CONTAINER="seed-git"
OBJECT="seed-git.tar.gz"
BUNDLE="seed.git.bundle"
GIT_REPO="/media/volume/home/git/seed.git"
GIT_USER="git"
GIT_GROUP="git"

catalog_filter() {
    local type="$1"
    jq '.token.catalog[] | select(.type == "'${type}'")'
}

endpoint_filter() {
    local region="$1"
    local interface="$2"
    jq '.endpoints[] | select(.region == "'${region}'" and .interface == "'${interface}'")'
}

endpoint_url() {
    jq --raw-output .url
}

subject_token() {
    grep -oP 'X-Subject-Token: \K.*'
}

if [[ -d "$GIT_REPO" ]] ; then
  echo "Repository exists locally, nothing to do."
  exit 0
fi

if [[ ! -f "$AUTH_FILE" ]] ; then
  >&2 echo "Missing $AUTH_FILE"
  exit 1
fi

AUTH_TOKEN="$(curl \
  --silent \
  --show-error \
  --header 'Content-Type: application/json' \
  --data @$AUTH_FILE \
  --dump-header - \
  --output $ENDPOINT_FILE $IDENTITY/auth/tokens | subject_token)"

if [[ -z "$AUTH_TOKEN" ]] ; then
  >&2 echo "Failed to get auth token."
  exit 1
fi

OBJECT_STORE="$(cat $ENDPOINT_FILE | \
  catalog_filter "object-store" | \
  endpoint_filter "$REGION" "public" | \
  endpoint_url)"

if [[ -z "$OBJECT_STORE" ]] ; then
  >&2 echo "Failed to get object store endpoint."
  exit 1
fi

curl \
  --header "X-Auth-Token: $AUTH_TOKEN" \
  --output "$OBJECT" \
  "$OBJECT_STORE/$CONTAINER/$OBJECT" || rm "$OBJECT"

tar -xzvf "$OBJECT"
git clone --bare "$BUNDLE" "$GIT_REPO"
chown -R "$GIT_USER:$GIT_GROUP" "$GIT_REPO"
