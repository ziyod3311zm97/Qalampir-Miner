const express = require('express');
const http = require('http');
const path = require('path');
const cors = require('cors');
const fs = require('fs');
const { Telegraf, Markup } = require('telegraf');

const app = express();
const server = http.createServer(app);

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));
app.use(express.static(path.join(__dirname, 'public')));

const DB_FILE = path.join(__dirname, 'users_db.json');
let usersDB = {};

// Ma'lumotlarni fayldan yuklash
if (fs.existsSync(DB_FILE)) {
    try {
        usersDB = JSON.parse(fs.readFileSync(DB_FILE, 'utf8'));
    } catch (e) {
        usersDB = {};
    }
}

// Ma'lumotlarni faylga saqlash
function saveDB() {
    fs.writeFileSync(DB_FILE, JSON.stringify(usersDB, null, 2));
}

// User hisobini olish va passiv miningni hisoblash
function getUserData(userId, name) {
    const now = Date.now();
    if (!usersDB[userId]) {
        usersDB[userId] = {
            id: userId,
            name: name || "Miner",
            balance: 0,
            miningRate: 0.1, // sec
            upgradeCost: 50,
            level: 1,
            lastClaimTime: now,
            unclaimedCoins: 0
        };
        saveDB();
    } else {
        const user = usersDB[userId];
        if (name && user.name !== name) user.name = name;
        
        const secondsPassed = (now - user.lastClaimTime) / 1000;
        const minedCoins = secondsPassed * user.miningRate;
        user.unclaimedCoins = (user.unclaimedCoins || 0) + minedCoins;
        user.lastClaimTime = now;
        saveDB();
    }
    return usersDB[userId];
}

// API: User ma'lumotlari
app.post('/api/user', (req, res) => {
    try {
        const { user_id, name } = req.body;
        if (!user_id) return res.status(400).json({ error: "user_id yetishmayapti" });

        const user = getUserData(user_id, name);
        const totalUsers = Object.keys(usersDB).length;

        res.json({ success: true, user, totalUsers });
    } catch (e) {
        res.status(500).json({ error: "Server xatosi" });
    }
});

// API: Claim qilish
app.post('/api/claim', (req, res) => {
    try {
        const { user_id } = req.body;
        const user = usersDB[user_id];
        if (!user) return res.status(404).json({ error: "User topilmadi" });

        const now = Date.now();
        const secondsPassed = (now - user.lastClaimTime) / 1000;
        const minedCoins = secondsPassed * user.miningRate + (user.unclaimedCoins || 0);

        user.balance += minedCoins;
        user.unclaimedCoins = 0;
        user.lastClaimTime = now;
        saveDB();

        res.json({ success: true, balance: user.balance, unclaimedCoins: 0 });
    } catch (e) {
        res.status(500).json({ error: "Claim bajarilmadi" });
    }
});

// API: Upgrade oshirish
app.post('/api/upgrade', (req, res) => {
    try {
        const { user_id } = req.body;
        const user = usersDB[user_id];
        if (!user) return res.status(404).json({ error: "User topilmadi" });

        if (user.balance >= user.upgradeCost) {
            user.balance -= user.upgradeCost;
            user.miningRate += 0.25;
            user.level += 1;
            user.upgradeCost = Math.round(user.upgradeCost * 1.85);
            saveDB();

            res.json({
                success: true,
                balance: user.balance,
                miningRate: user.miningRate,
                upgradeCost: user.upgradeCost,
                level: user.level
            });
        } else {
            res.status(400).json({ error: "Balans yetarli emas!" });
        }
    } catch (e) {
        res.status(500).json({ error: "Upgrade bajarilmadi" });
    }
});

// API: Leaderboard (Top 10)
app.get('/api/leaderboard', (req, res) => {
    try {
        const leaderboard = Object.values(usersDB)
            .map(u => ({
                name: u.name,
                balance: u.balance + (u.unclaimedCoins || 0),
                level: u.level || 1
            }))
            .sort((a, b) => b.balance - a.balance)
            .slice(0, 10);

        res.json({ success: true, leaderboard });
    } catch (e) {
        res.status(500).json({ error: "Leaderboard xatosi" });
    }
});

// TELEGRAM BOT SOZLAMASI
const BOT_TOKEN = '8995342958:AAEYriJLB4BvroCOF7qLBsptPqFeyT8dWDg';
const GAME_URL = 'https://qalampir-miner-huy8.onrender.com';

const bot = new Telegraf(BOT_TOKEN);

bot.start((ctx) => {
    ctx.reply(
        `⚡ Xush kelibsiz ${ctx.from.first_name}!\n\nQalampir Crypto Mining imperiyasiga qo'shiling. Passiv mining qiling, darajangizni oshiring va Top-10 reytingiga kiring! ⛏️🔥`,
        Markup.inlineKeyboard([
            [Markup.button.webApp("🔥 MINING APPNI OCHISH", GAME_URL)]
        ])
    );
});

bot.launch().then(() => console.log("Telegram Bot tayyor!")).catch(console.error);

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
