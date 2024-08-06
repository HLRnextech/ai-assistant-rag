Nextech RAG

Dev Setup:

1. Clone repo
2. Setup individual services (see `asset_processor/README.md`, `backend/README.md`, `sitemap_processor/README.md` and `chatbot_ui/README.md` for more details)
3. Run `docker-compose up -d` in the root directory

---

Prod Setup:

- Prerequisites:

  Set the required environment variables:

```bash
AWS_PROFILE_NAME=aws_profile_name_here
AWS_REGION=us-east-1
EKS_CLUSTER_NAME=nextech
APP_NAMESPACE=nextech
ESO_NAMESPACE=external-secrets
```

- AWS CLI setup:

  Install AWS CLI

  Configure the AWS CLI using `aws configure --profile $AWS_PROFILE_NAME`

  Make sure to use this profile by: `export AWS_PROFILE=$AWS_PROFILE_NAME`

  Set the account id as env variable: `AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)`

- S3 setup:

  Create a private s3 bucket and attach a cloudfront distribution to it and use the OAI access policy instead of OAC.

- EKSCTL setup:
  Initialise the EKS cluster: `eksctl create cluster --name $EKS_CLUSTER_NAME --region $AWS_REGION --fargate`

  Update kubeconfig: `aws eks update-kubeconfig --name $EKS_CLUSTER_NAME`

  Run `kubectl create namespace $APP_NAMESPACE` to create the namespace

  Create a new fargate profile:

```bash
eksctl create fargateprofile \
    --cluster $EKS_CLUSTER_NAME \
    --region $AWS_REGION \
    --name $EKS_CLUSTER_NAME-fgp \
    --namespace $APP_NAMESPACE

# for ESO
eksctl create fargateprofile \
    --cluster $EKS_CLUSTER_NAME \
    --region $AWS_REGION \
    --name externalsecrets-fgp \
    --namespace $ESO_NAMESPACE
```

- OIDC setup (allowing pods/ALB access to AWS resources):

```bash
eksctl utils associate-iam-oidc-provider --cluster $EKS_CLUSTER_NAME --region $AWS_REGION --approve
# check the oidc id
aws eks describe-cluster --region $AWS_REGION --name $EKS_CLUSTER_NAME --query "cluster.identity.oidc.issuer" --output text
```

- Nginx ingress controller setup:

Create a nodegroup with t3.medium machines via AWS Console. Nginx ingress controller cannot be run on fargate.

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

helm upgrade -i ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --set controller.allowSnippetAnnotations=true

kubectl -n ingress-nginx rollout status deployment ingress-nginx-controller

kubectl get svc -n ingress-nginx
```

Get the IP of the Loadbalancer service in the `ingress-nginx` namespace and update the DNS records.

Apply the nginx configmap:

```bash
kubectl apply -f k8s/ingress/nginx-configmap.yaml
```

Then install cert-manager:

```bash
helm repo add jetstack https://charts.jetstack.io --force-update
helm install \
  cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.15.1 \
  --set crds.enabled=true
```

Create the LetsEncrypt ClusterIssuer:

```bash
kubectl apply -f k8s/ingress/certissuer.yaml -n $APP_NAMESPACE
kubectl describe issuer nextech-letsencrypt-prod -n $APP_NAMESPACE
```

Apply the ingress:

```bash
kubectl apply -f k8s/ingress/ingress.yaml -n $APP_NAMESPACE
```

- ECR setup:

```bash
# create the repositories (1 repo for each service)
for repo in asset-processor backend sitemap-processor chatbot-ui ; do
  aws ecr create-repository --repository-name nextech-$repo --image-scanning-configuration scanOnPush=true --region $AWS_REGION
done

# connect to the repository
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

- ESO setup (External Secrets Operator):

```bash
helm repo add external-secrets https://charts.external-secrets.io

helm upgrade --install external-secrets \
   external-secrets/external-secrets \
   -n $ESO_NAMESPACE \
   --create-namespace \
   --set installCRDs=true \
   --set webhook.port=9443

# verify the installation
kubectl get pods -n $ESO_NAMESPACE
```

Create IAM Service Account for ESO to pull secrets from AWS Secrets Manager:

```bash
ARN=$(aws iam list-policies --query "Policies[?PolicyName=='SecretsManagerReadWrite'].Arn" --output text)
eksctl create iamserviceaccount \
    --name eso \
    --region $AWS_REGION \
    --namespace $APP_NAMESPACE \
    --cluster $EKS_CLUSTER_NAME \
    --role-name eso \
    --attach-policy-arn $ARN \
    --approve \
    --override-existing-serviceaccounts

# verify
kubectl get sa -n $APP_NAMESPACE

kubectl describe sa eso -n $APP_NAMESPACE

# create the secret store
kubectl apply -f k8s/config/secretstore.yaml -n $APP_NAMESPACE

# verify
kubectl get secretstore -n $APP_NAMESPACE
```

Creating secrets in AWS Secrets Manager:

Populate the `eso/.env` file:

```bash
cp ./eso/.env.example ./eso/.env
```

> Note: Before running this script, make sure an RDS database is created and a secret name is provided by AWS where the db connection info will be stored.

`DB_SECRET_NAME="rds\!db-63ec70dd-0d9a-423d-90c8-95d63704ae7c"`

> Note: You also need RABBITMQ connection string. Create a RabbitMQ instance on cloudamqp.

Run the script which reads the `.env` file and creates the secrets in AWS Secrets Manager:

```bash
# NEXTECH is the key prefix and DB_SECRET_NAME is the secret name for db connection info.
AWS_REGION=$AWS_REGION DB_SECRET_NAME=$DB_SECRET_NAME ./eso/create-secrets.sh NEXTECH
APP_NAMESPACE=$APP_NAMESPACE ./eso/apply-secrets.sh
```

This script will also update the `k8s/config/eso.yaml` file with the corresponding secret names.

```bash
kubectl apply -f k8s/config/eso.yaml -n $APP_NAMESPACE

# verify
kubectl get secrets -n $APP_NAMESPACE
```

- Logging setup (fluentd/cloudwatch)

Refer: https://docs.aws.amazon.com/eks/latest/userguide/fargate-logging.html

```bash
# create a fargate profile for aws-observability namespace
eksctl create fargateprofile \
    --cluster $EKS_CLUSTER_NAME \
    --region $AWS_REGION \
    --name aws-observability-fgp \
    --namespace aws-observability

echo "
kind: Namespace
apiVersion: v1
metadata:
  name: aws-observability
  labels:
    aws-observability: enabled

---
kind: ConfigMap
apiVersion: v1
metadata:
  name: aws-logging
  namespace: aws-observability
data:
  flb_log_cw: \"false\"
  filters.conf: |
    [FILTER]
        Name parser
        Match *
        Key_name log
        Parser crio
    [FILTER]
        Name kubernetes
        Match kube.*
        Merge_Log On
        Keep_Log Off
        Buffer_Size 0
        Kube_Meta_Cache_TTL 300s
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match   kube.*
        region $AWS_REGION
        log_group_name nextech-logs
        log_stream_prefix from-fluent-bit-
        log_retention_days 14
        auto_create_group true
  parsers.conf: |
    [PARSER]
        Name crio
        Format Regex
        Regex ^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>P|F) (?<log>.*)$
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L%z
" | kubectl apply -f -

curl -O https://raw.githubusercontent.com/aws-samples/amazon-eks-fluent-logging-examples/mainline/examples/fargate/cloudwatchlogs/permissions.json

aws iam create-policy --policy-name eks-fargate-logging-policy --policy-document file://permissions.json

# find the name of the fargate pod execution role (eksctl-$EKS_CLUSTER_NAME-cluster-FargatePodExecutionRole-xxxxxx)
ROLE_NAME=$(aws iam list-roles --query "Roles[?contains(RoleName, 'eksctl-${EKS_CLUSTER_NAME}-cluster-FargatePodExecutionRole')].RoleName" --output text)

aws iam attach-role-policy \
  --policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/eks-fargate-logging-policy \
  --role-name $ROLE_NAME
```

Logs will be sent to CloudWatch Logs under the log group `nextech-logs`.

To check if logging is enabled on a given pod, just describe the pod and check for the `LoggingEnabled` annotation.
