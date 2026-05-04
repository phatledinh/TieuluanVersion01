FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy API tester page
RUN mkdir -p /usr/share/nginx/html
COPY api-tester.html /usr/share/nginx/html/api-tester.html
COPY code-viewer.html /usr/share/nginx/html/code-viewer.html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
