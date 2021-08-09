 docker build -f images/Dockerfile -t local images/

docker run -p 7000:8080 --env REDDIT_API_URL_TOP='https://oauth.reddit.com/r/placeholder_value/top' \
--env REDDIT_ACCOUNTS_TABLE_NAME="RedditAccountsTable-dev" --env REDDIT_AUTH_URL="https://www.reddit.com/api/v1/access_token"  local:latest
