# --- Stage 1: Build React static bundle ---
FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json to leverage Docker layer caching
COPY frontend/package.json ./

# Install npm dependencies
RUN npm install

# Copy all frontend files
COPY frontend/ ./

# Build the optimized production static bundle
RUN npm run build

# --- Stage 2: Serve compiled bundle with Nginx ---
FROM nginx:alpine

# Copy static assets from build stage to Nginx default public directory
COPY --from=build /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
