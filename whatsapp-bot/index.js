// ------------------ Imports ------------------
const express = require('express');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');
const axios = require('axios');
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// ------------------ App Setup ------------------
const app = express();
app.use(express.json());

let fastApiPort = 8001; // fallback

try {
    const portData = fs.readFileSync('fastapi_port.txt', 'utf-8');
    fastApiPort = parseInt(portData.trim(), 10);
    console.log(`🌐 FastAPI backend detected on port: ${fastApiPort}`);
} catch (err) {
    console.warn('⚠️ Could not read FastAPI port file. Defaulting to 8001.');
}

// ------------------ WhatsApp Client Setup ------------------
let isReady = false;

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: false,
        executablePath: puppeteer.executablePath(),
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-gpu'
        ]
    }
});

// ------------------ NodeJS Crash Handlers ------------------
process.on('uncaughtException', (err) => {
    console.error('❌ Uncaught Exception:', err);
});
process.on('unhandledRejection', (reason) => {
    console.error('❌ Unhandled Rejection:', reason);
});

// ------------------ WhatsApp Event Handlers ------------------
client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
    console.log('📸 QR code generated. Scan to login.');
});

client.on('ready', () => {
    console.log('✅ WhatsApp client ready!');
    isReady = true;
});

client.on('message', async (msg) => {
    console.log('📩 New WhatsApp message:', msg.body);
    try {
        const payload = { message: msg.body, number: msg.from };
        console.log('📤 Forwarding message to agent:', payload);
        await axios.post(`http://localhost:${fastApiPort}/incoming`, payload);
    } catch (error) {
        console.error('❌ Failed to forward to agent:', error.message);
    }
});

// ❗ Only ONE disconnected handler
client.on('disconnected', async (reason) => {
    console.error('❌ Client disconnected. Reason:', reason);
    console.log('🔄 Attempting full restart...');
    try {
        await client.destroy();
        await client.initialize();
    } catch (err) {
        console.error('❌ Error during client restart:', err);
    }
});

client.on('auth_failure', async (msg) => {
    console.error('❌ Authentication failure:', msg);
    console.log('🧹 Clearing session and restarting...');
    try {
        if (fs.existsSync(sessionPath)) {
            fs.rmSync(sessionPath, { recursive: true, force: true });
        }
        await client.destroy();
        await client.initialize();
    } catch (err) {
        console.error('❌ Error during reauthentication:', err);
    }
});

client.on('change_state', (state) => {
    console.log('🔄 Client state changed:', state);
});

// ------------------ Initialize WhatsApp Client ------------------
client.initialize();

// ------------------ API Routes ------------------
app.post('/send', async (req, res) => {
    const { number, message } = req.body;
    console.log('📨 Incoming /send request:', { number, message });

    if (!isReady || !client.info || !client.info.wid) {
        return res.status(503).send({ error: 'Client not ready or session inactive.' });
    }

    const chatId = number.includes('@c.us') ? number : `${number}@c.us`;

    try {
        await client.sendMessage(chatId, message);
        console.log(`✅ Message sent to ${chatId}:`, message);
        res.send({ success: true });
    } catch (err) {
        console.error('❌ Failed to send message:', err);
        res.status(500).send({ error: err.message });
    }
});

// ------------------ Start Express Server ------------------
app.listen(3000, () => {
    console.log('🚀 WhatsApp API server running on http://localhost:3000');
});
