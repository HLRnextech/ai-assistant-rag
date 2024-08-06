set -e

if [ -z "$APP_NAMESPACE" ]; then
  echo "APP_NAMESPACE is not set"
  exit 1
fi

kubectl apply -f ./k8s/config/secretstore.yaml -n $APP_NAMESPACE
kubectl apply -f ./k8s/config/eso.yaml -n $APP_NAMESPACE

# force sync external secrets
kubectl annotate es esoexternalsecret force-sync=$(date +%s) --overwrite -n $APP_NAMESPACE
