# Stage 1: Build the Vite project
FROM node:20-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
# Copy built static files to Nginx web root
COPY --from=build /app/dist /usr/share/nginx/html

# Copy a custom nginx config if necessary, but default works for static sites
# We just need to ensure fallback to index.html for SPA routing if we had it,
# but for vanilla JS with direct HTML files, default is fine.

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
