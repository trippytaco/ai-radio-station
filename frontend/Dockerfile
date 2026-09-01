# Multi-stage build: compile the Vite app once at image-build time, then
# serve the static output from a tiny nginx image. Deliberately NOT the
# "npm install on every container start" pattern used for the backend -
# that pattern is what caused most of tonight's backend deploy problems
# (slow/fragile dependency resolution on every restart, partial installs
# racing the health check). A real image build avoids all of that: once
# built, starting the container is instant and does zero network I/O.

FROM node:20-alpine AS build
WORKDIR /app

# Build-time only - baked into the static JS bundle by Vite, not read at
# container runtime. Defaults to the live production API if not passed.
ARG VITE_API_BASE=https://radiome.orosz.cc
ENV VITE_API_BASE=$VITE_API_BASE

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

EXPOSE 80
