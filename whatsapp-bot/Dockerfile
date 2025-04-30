FROM node:18-alpine

WORKDIR /app

# install Node deps
COPY package.json package-lock.json ./
RUN npm install

# copy the rest of your sender code
COPY . .

# launch your WhatsApp sender
CMD ["npm", "start"]
