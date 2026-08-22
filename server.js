const express = require('express');
const http = require('http');
const path = require('path');
const cors = require('cors');
const { Telegraf, Markup } = require('telegraf');

const app = express();
const server = http.createServer(app);

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));
app.use(express.static(path.join(__dirname, 'public')));

// MA'LUMOTLAR BAZASI (Vaqtincha xotira saqlagich)
const usersDB = {};

// O'yinchi profilini olish / Yaratish (Passive Mining Hisobi)
function getUserData(userId, name) {
    const now = Date.now();
    if (!usersDB[userId]) {
        usersDB[userId] = {
            id: userId,
            name: name || "Miner",
            balance: 0,
            miningRate: 0.1, // Har soniyada 0.1 tanga
            upgradeCost: 50,
            lastClaimTime: now,
            unclaimedCoins: 0
        };
    } else {
        // Passiv mining hisoblash (Oflayn bo'lgan vaqt uchun)
        const user = usersDB[userId];
        const secondsPassed = (now - user.lastClaimTime) / 1000;
        const minedCoins = secondsPassed * user.miningRate;
        user.unclaimedCoins = (user.unclaimedCoins || 0) + minedCoins;
        user.lastClaimTime = now;
    }
    return usersDB[userId];
}

// API: Foydalanuvchi ma'lumotlarini olish
app.post('/api/user', (req, res) => {
    try {
        const { user_id, name } = req.body;
        if (!user_id) return res.status(400).json({ error: "user_id kiritilmadi" });

        const userData = getUserData(user_id, name);
        res.json({ success: true, user: userData });
    } catch (err) {
        res.status(500).json({ error: "Server xatoligi" });
    }
});

// API: Yig'ilgan tangalarni balansga o'tkazish (Claim)
app.post('/api/claim', (req, res) => {
    try {
        const { user_id } = req.body;
        const user = usersDB[user_id];
        if (!user) return res.status(404).json({ error: "Foydalanuvchi topilmadi" });

        const now = Date.now();
        const secondsPassed = (now - user.lastClaimTime) / 1000;
        const minedCoins = secondsPassed * user.miningRate + (user.unclaimedCoins || 0);

        user.balance += minedCoins;
        user.unclaimedCoins = 0;
        user.lastClaimTime = now;

        res.json({ success: true, balance: user.balance, unclaimedCoins: 0 });
    } catch (err) {
        res.status(500).json({ error: "Claim amali bajarilmadi" });
    }
});

// API: Mining Tezligini oshirish (Upgrade)
app.post('/api/upgrade', (req, res) => {
    try {
        const { user_id } = req.body;
        const user = usersDB[user_id];
        if (!user) return res.status(404).json({ error: "Foydalanuvchi topilmadi" });

        if (user.balance >= user.upgradeCost) {
            user.balance -= user.upgradeCost;
            user.miningRate += 0.2; // Tezlikni 0.2 ga oshirish
            user.upgradeCost = Math.round(user.upgradeCost * 1.8); // Narx oshishi

            res.json({
                success: true,
                balance: user.balance,
                miningRate: user.miningRate,
                upgradeCost: user.upgradeCost
            });
        } else {
            res.status(400).json({ error: "Mablag' yetarli emas!" });
        }
    } catch (err) {
        res.status(500).json({ error: "Upgrade amali bajarilmadi" });
    }
});

// TELEGRAM BOT SOZLAMALARI
const BOT_TOKEN = '8995342958:AAEYriJLB4BvroCOF7qLBsptPqFeyT8dWDg';
const GAME_URL = 'https://qalampir-miner-huy8.onrender.com';

const bot = new Telegraf(BOT_TOKEN);

bot.start((ctx) => {
    ctx.reply(
        `Xush kelibsiz, ${ctx.from.first_name}! ⛏️ Crypto Mining mini-appiga tayyormisiz?`,
        Markup.inlineKeyboard([
            [Markup.button.webApp("⛏️ Miningni Boshlash", GAME_URL)]
        ])
    );
});

// Webhook va polling muammolarini oldini olish bilan ishga tushirish
bot.launch().then(() => {
    console.log("Telegram Bot muvaffaqiyatli ishga tushdi!");
}).catch((err) => {
    console.error("Botni ishga tushirishda xatolik:", err);
});

// Graceful shutdown (Process to'xtatilganda botni toza o'chirish)
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log(`Mining Server ${PORT}-portda ishlamoqda`));
