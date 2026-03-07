FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install --omit=dev

COPY index.js ./
COPY tool-handlers.js ./
COPY tools-definitions.js ./
COPY tools-subscribers.js ./
COPY tools-remaining.js ./

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 && \
    chown -R nodejs:nodejs /app

USER nodejs

CMD ["node", "index.js"]
