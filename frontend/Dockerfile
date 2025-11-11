# Frontend Dockerfile for Requirements Support AI System

FROM node:18-alpine as base

# Set working directory
WORKDIR /app

# Install dependencies based on package.json and package-lock.json
COPY package*.json ./

# Development stage
FROM base as development

# Install all dependencies (including devDependencies)
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run development server with hot reload
CMD ["npm", "run", "dev"]

# Builder stage for production
FROM base as builder

# Install dependencies (production only)
RUN npm ci --only=production

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine as production

WORKDIR /app

# Copy necessary files from builder
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

# Expose port
EXPOSE 3000

# Run production server
CMD ["npm", "start"]
