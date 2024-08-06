set -e

if [ ! -f ./dist/widget.js ]; then
  echo "Error: ./dist/widget.js does not exist. Please run 'npm run build' before running this script."
  exit 1
fi

if [ ! -f ./dist/widget.css ]; then
  echo "Error: ./dist/widget.css does not exist. Please run 'npm run build' before running this script."
  exit 1
fi

# if the js and css files aready exist on s3 bucket, download them and get their md5 hash
mkdir ./remote

JS_FILE_EXISTS=$(aws s3 ls s3://$S3_BUCKET/chatbot/widget.js | wc -l)
echo "JS_FILE_EXISTS: $JS_FILE_EXISTS"

CSS_FILE_EXISTS=$(aws s3 ls s3://$S3_BUCKET/chatbot/widget.css | wc -l)
echo "CSS_FILE_EXISTS: $CSS_FILE_EXISTS"

LOCAL_JS_MD5=$(md5sum ./dist/widget.js | awk '{ print $1 }')
echo "LOCAL_JS_MD5: $LOCAL_JS_MD5"
REMOTE_JS_MD5=""

LOCAL_CSS_MD5=$(md5sum ./dist/widget.css | awk '{ print $1 }')
echo "LOCAL_CSS_MD5: $LOCAL_CSS_MD5"
REMOTE_CSS_MD5=""

if [ $JS_FILE_EXISTS -eq 1 ]; then
  aws s3 cp s3://$S3_BUCKET/chatbot/widget.js ./remote/widget.js
  REMOTE_JS_MD5=$(md5sum ./remote/widget.js | awk '{ print $1 }')
  echo "REMOTE_JS_MD5: $REMOTE_JS_MD5"
fi

if [ $CSS_FILE_EXISTS -eq 1 ]; then
  aws s3 cp s3://$S3_BUCKET/chatbot/widget.css ./remote/widget.css
  REMOTE_CSS_MD5=$(md5sum ./remote/widget.css | awk '{ print $1 }')
  echo "REMOTE_CSS_MD5: $REMOTE_CSS_MD5"
fi

if [ "$LOCAL_JS_MD5" == "$REMOTE_JS_MD5" ] && [ "$LOCAL_CSS_MD5" == "$REMOTE_CSS_MD5" ]; then
  echo "Local files are the same as remote files. No need to redeploy."
  rm -rf ./remote
  exit 0
fi

aws s3 cp ./dist/widget.js s3://$S3_BUCKET/chatbot/widget.js
echo "Uploaded ./dist/widget.js to s3://$S3_BUCKET/chatbot/widget.js"

aws s3 cp ./dist/widget.css s3://$S3_BUCKET/chatbot/widget.css
echo "Uploaded ./dist/widget.css to s3://$S3_BUCKET/chatbot/widget.css"

aws cloudfront create-invalidation --distribution-id $CF_DISTRIBUTION_ID --paths "/chatbot/*"
echo "Created cloudfront invalidation for /chatbot/*"
