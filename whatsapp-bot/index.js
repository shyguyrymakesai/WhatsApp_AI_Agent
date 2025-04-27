const express = require('express');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: false } // set to false so you can debug the browser
});

client.on('ready', () => {
    console.log('✅ WhatsApp client ready');
    isReady = true;
});

client.initialize();

// POST /send - send a WhatsApp message
app.post('/send', async (req, res) => {
    const { number, message } = req.body;

    if (!isReady) return res.status(503).send({ error: 'Client not ready' });

    const chatId = number.includes('@c.us') ? number : `${number}@c.us`;

    try {
        await client.sendMessage(chatId, message);
        console.log(`📤 Sent to ${number}: ${message}`);
        res.send({ success: true });
    } catch (err) {
        console.error('❌ Error sending message:', err);
        res.status(500).send({ error: err.message });
    }
});

app.listen(3000, () => {
    console.log('🚀 WhatsApp API running on http://localhost:3000');
});
