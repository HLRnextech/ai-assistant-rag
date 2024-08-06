set -e

if [ -z "$DB_SECRET_NAME" ]; then
  echo "DB_SECRET_NAME is not set. DB_SECRET_NAME is required - it should contain the user/password for RDS database"
  exit 1
fi

if [ -z "$AWS_REGION" ]; then
  echo "AWS_REGION is not set"
  exit 1
fi

if [ -z "$1" ]; then
  echo "Usage: ./create_secrets.sh <prefix>"
  echo "Prefix will be used to prefix the secret names in AWS Secrets Manager"
  exit 1
fi

# read the /.env file line by line and print they key/value pairs
# ignore any lines that start with a # or are empty
# ignore the part in the value after # if it exists

while IFS= read -r line; do
  # ignore empty lines
  if [ -z "$line" ]; then
    continue
  fi

  # ignore lines that start with a #
  if [[ "$line" == \#* ]]; then
    continue
  fi

  # ignore the part in the value after #
  line=$(echo $line | cut -d "#" -f 1)

  # split the line by the = sign
  IFS='=' read -r key value <<< "$line"

  # if the key is empty, ignore the line
  if [ -z "$key" ]; then
    continue
  fi

  # create the secret if it doesn't exist else update
  if aws secretsmanager describe-secret --secret-id $1_$key --region $AWS_REGION &> /dev/null; then
    echo "Updating secret for $1_$key in AWS Secrets Manager in region $AWS_REGION"
    aws secretsmanager update-secret --secret-id $1_$key --secret-string $value --region $AWS_REGION > /dev/null
    continue
  fi
  echo "Creating secret for $1_$key in AWS Secrets Manager in region $AWS_REGION"
  aws secretsmanager create-secret --name $1_$key --secret-string $value --region $AWS_REGION > /dev/null
done < ./eso/.env

echo "apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: esoexternalsecret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: esosecretstore
    kind: SecretStore
  target:
    name: esosecret
    creationPolicy: Owner
  data:" > ./k8s/config/eso.yaml

while IFS= read -r line; do
  # ignore empty lines
  if [ -z "$line" ]; then
    continue
  fi

  # ignore lines that start with a #
  if [[ "$line" == \#* ]]; then
    continue
  fi

  # ignore the part in the value after #
  line=$(echo $line | cut -d "#" -f 1)

  # split the line by the = sign
  IFS='=' read -r key value <<< "$line"

  # if the key is empty, ignore the line
  if [ -z "$key" ]; then
    continue
  fi

  echo "    - secretKey: $1_$key
      remoteRef:
        key: $1_$key" >> ./k8s/config/eso.yaml

done < ./eso/.env

# append db password and username to the eso.yaml file
echo "    - secretKey: $1_DB_USERNAME
      remoteRef:
        key: $DB_SECRET_NAME
        property: username
    - secretKey: $1_DB_PASSWORD
      remoteRef:
        key: $DB_SECRET_NAME
        property: password
" >> ./k8s/config/eso.yaml
