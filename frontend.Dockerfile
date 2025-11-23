# Stage 1: Build
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY frontend/ .

# Build the app
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Copy build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
