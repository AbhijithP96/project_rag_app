FROM node:20-slim AS builder

WORKDIR /app

# copy package files
COPY package*.json ./

# install dependencies
RUN npm ci

# copy source
COPY . .

# build production bundle
RUN npm run build

# production stage
FROM nginx:stable-alpine

# copy built frontend
COPY --from=builder /app/dist /usr/share/nginx/html

# copy nginx config
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O- http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]