FROM node:20-slim as builder

RUN npm i -g pnpm

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile

COPY . .

RUN pnpm run build

FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y awscli

WORKDIR /app

COPY --from=builder /app/deploy /app
COPY --from=builder /app/dist /app/dist

RUN chmod +x deploy.sh

CMD ["bash", "deploy.sh"]
