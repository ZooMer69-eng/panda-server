from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Dict, List
import json
import os
import time
import random

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

players_db: Dict[str, dict] = {}
rooms: Dict[str, dict] = {}

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Panda Game 22.0</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Nunito', sans-serif; user-select: none; -webkit-tap-highlight-color: transparent; }
        body { background: #0a120e; color: #fff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; position: relative; }

        #setup-screen { position: fixed; inset: 0; background: rgba(10, 18, 14, 0.98); z-index: 9999; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }
        .gender-btns { display: flex; gap: 20px; margin-top: 20px; }
        .gender-btn { background: rgba(255,255,255,0.1); border: 2px solid #4caf50; border-radius: 20px; padding: 20px 30px; cursor: pointer; transition: 0.2s; }
        .gender-btn:hover { background: rgba(76, 175, 80, 0.3); transform: scale(1.05); }
        .gender-btn .icon { font-size: 50px; display: block; margin-bottom: 10px; }

        /* ФОН */
        .bg-container { position: absolute; inset: 0; z-index: 1; overflow: hidden; transition: background 1.5s; }
        .bg-base { background: linear-gradient(180deg, #0f172a 0%, #1e293b 40%, #334155 70%, #475569 100%); }
        .bg-romantic { background: linear-gradient(180deg, #2d1b36 0%, #6b3f5c 40%, #a86b7e 70%, #d9a0a8 100%) !important; }
        .bg-bro { background: linear-gradient(180deg, #1a1a2e 0%, #2d2d4a 40%, #4a3b52 70%, #6b4c5a 100%) !important; }
        .bg-sisters { background: linear-gradient(180deg, #361b2d 0%, #5c3f6b 40%, #7ea8a8 70%, #a8d9d9 100%) !important; }

        .bg-sky { position: absolute; inset: 0; }
        .bg-moon { position: absolute; top: 10%; right: 15%; width: 80px; height: 80px; background: radial-gradient(circle, #fef08a 10%, #fde047 40%, transparent 70%); border-radius: 50%; filter: blur(2px); box-shadow: 0 0 40px rgba(253, 224, 71, 0.4); }
        .bg-clouds { position: absolute; top: 15%; left: 0; width: 200%; height: 30%; opacity: 0.3; background: radial-gradient(ellipse at 20% 50%, #fff 10%, transparent 40%), radial-gradient(ellipse at 70% 30%, #fff 15%, transparent 50%); animation: floatClouds 60s linear infinite; }
        @keyframes floatClouds { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        
        .bg-mountains { position: absolute; bottom: 20%; left: 0; width: 100%; height: 45%; }
        .bg-mountains svg { width: 100%; height: 100%; filter: drop-shadow(0 -5px 10px rgba(0,0,0,0.5)); }
        
        .bg-bamboo { position: absolute; bottom: 0; left: 0; width: 100%; height: 85%; display: flex; justify-content: space-around; align-items: flex-end; z-index: 2; }
        .stalk { position: relative; width: 22px; background: linear-gradient(90deg, #064e3b 0%, #10b981 20%, #34d399 50%, #10b981 80%, #064e3b 100%); border-radius: 10px; box-shadow: 5px 0 15px rgba(0,0,0,0.5); }
        .stalk::before { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(180deg, transparent 0 100px, #022c22 100px 106px); border-radius: 10px; }
        .stalk::after { content: ''; position: absolute; top: 20%; left: 22px; width: 60px; height: 14px; background: #10b981; border-radius: 5px 20px 5px 5px; transform: rotate(-15deg); box-shadow: 2px 2px 10px rgba(0,0,0,0.4); border-bottom: 2px solid #064e3b; }
        
        .bg-ground { position: absolute; bottom: 0; left: 0; width: 100%; height: 25%; background: linear-gradient(to top, #022c22 0%, #064e3b 100%); z-index: 3; box-shadow: inset 0 10px 30px rgba(0,0,0,0.5); }

        /* ХЕДЕР */
        .header { padding: 12px 15px; display: flex; justify-content: space-between; align-items: flex-start; z-index: 10; position: relative; }
        
        .user-info-block { display: flex; align-items: center; gap: 10px; }
        .avatar-wrap { position: relative; width: 50px; height: 50px; cursor: pointer; }
        .profile-avatar-mini { width: 100%; height: 100%; border-radius: 50%; background: #333; display: flex; justify-content: center; align-items: center; font-size: 24px; overflow: hidden; border: 2px solid #fff; z-index: 2; position: relative; }
        .profile-avatar-mini img { width: 100%; height: 100%; object-fit: cover; }
        .avatar-frame { position: absolute; inset: -4px; border-radius: 50%; z-index: 1; border: 3px solid transparent; }
        .avatar-frame.default { border-color: #fff; }
        .avatar-frame.millionaire { border-color: #ffd700; box-shadow: 0 0 10px #ffd700; }
        .avatar-frame.legend { border-color: #00e5ff; box-shadow: 0 0 20px #00e5ff; animation: spin 4s linear infinite; }
        
        .name-medal-block { display: flex; flex-direction: column; cursor: pointer; }
        .name-row { display: flex; align-items: center; gap: 5px; }
        .header-nick { font-size: 16px; font-weight: 900; text-shadow: 2px 2px 0 #000; -webkit-text-fill-color: currentColor; }
        .header-medal { font-size: 14px; display: inline-flex; align-items: center; justify-content: center; filter: drop-shadow(0 0 5px rgba(255,255,255,0.4)); }
        .streak-badge { font-size: 10px; color: #ff6b00; font-weight: 900; margin-top: 2px; }

        .res-row { display: flex; align-items: center; gap: 10px; margin-top: 5px; }
        .coins-box { font-size: 18px; font-weight: 900; color: #fff; display: flex; align-items: center; gap: 3px; }
        .gems-box { font-size: 14px; font-weight: 900; color: #00e5ff; display: flex; align-items: center; gap: 3px; cursor: pointer; }
        
        .icon-coin { display: inline-block; width: 16px; height: 16px; background: radial-gradient(circle at 30% 30%, #fff000, #ffb300, #b26a00); border-radius: 50%; border: 1px solid #e6a800; box-shadow: 0 1px 3px rgba(0,0,0,0.5); text-align: center; line-height: 14px; font-size: 10px; font-weight: 900; color: #8a5100; vertical-align: middle; margin-left: 2px; }
        .icon-gem { display: inline-block; font-size: 16px; filter: drop-shadow(0 0 3px #00e5ff); margin-left: 2px; }

        .energy-box { display: flex; flex-direction: column; align-items: flex-end; cursor: pointer; }
        .energy-text { font-size: 10px; font-weight: 700; color: #fff; margin-bottom: 3px; }
        .energy-bar { width: 70px; height: 8px; background: rgba(0,0,0,0.5); border-radius: 5px; overflow: hidden; border: 1px solid rgba(255,255,255,0.4); }
        .energy-fill { height: 100%; background: linear-gradient(90deg, #00e5ff, #007bff); width: 100%; transition: width 0.3s; }

        /* ЭКРАНЫ */
        .screens { flex: 1; position: relative; z-index: 5; overflow: hidden; }
        .screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: none; flex-direction: column; }
        .screen.active { display: flex; }

        /* ТАП */
        .tap-area { flex: 1; display: flex; justify-content: center; align-items: flex-end; gap: 20px; position: relative; padding-bottom: 10px; z-index: 5; }
        .panda-wrapper { position: relative; width: 190px; height: 210px; transform-origin: center bottom; cursor: pointer; transition: transform 1s ease-in-out; z-index: 10; margin-bottom: 0; }
        .panda-wrapper:active { transform: scale(0.95); }
        .panda-wrapper.hit { animation: jump 0.25s ease-out; }
        @keyframes jump { 0% { transform: translateY(0); } 30% { transform: translateY(-15px) scale(1.05); } 100% { transform: translateY(0); } }
        
        /* ПИТОМЦЫ */
        .pet-container { position: absolute; bottom: 0px; right: -70px; width: 90px; height: 90px; z-index: 4; pointer-events: none; display: flex; justify-content: center; align-items: center; filter: drop-shadow(0 10px 10px rgba(0,0,0,0.5)); animation: petIdle 3s infinite alternate ease-in-out; }
        @keyframes petIdle { 0% { transform: translateY(0) scale(1) rotate(-2deg); } 100% { transform: translateY(-8px) scale(1.05) rotate(2deg); } }
        
        /* Анимации ников */
        .nick-default { color: #fff; }
        .nick-gold { background: linear-gradient(90deg, #ffd700, #ff8c00, #ffd700); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: goldShine 3s linear infinite; filter: drop-shadow(0 0 2px rgba(255,215,0,0.5)); }
        .nick-fire { color: #ff4500; text-shadow: 0 0 5px #ff4500, 0 0 15px #ff0000; animation: fireFlicker 1.5s infinite alternate; }
        .nick-rainbow { background: linear-gradient(90deg, #ff0000, #ff8c00, #ffff00, #00ff00, #00e5ff, #0000ff, #ff00ff); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: rainbowMove 3s linear infinite; filter: drop-shadow(0 0 2px rgba(255,255,255,0.3)); }
        @keyframes goldShine { to { background-position: 200% center; } }
        @keyframes fireFlicker { 0% { transform: scale(1); opacity: 0.9; } 100% { transform: scale(1.02); opacity: 1; } }
        @keyframes rainbowMove { to { background-position: 200% center; } }

        .eye { transform-box: fill-box; transform-origin: center; transition: transform 0.15s ease-in-out; }
        .eye.closed { transform: scaleY(0.1); }
        .eye.slow-open { transition: transform 2s ease-out; }

        .particle-coin { position: absolute; font-size: 24px; font-weight: 900; color: #ffd700; pointer-events: none; animation: popCoin 0.9s ease-out forwards; z-index: 20; text-shadow: 0 0 10px #ffd700; }
        @keyframes popCoin { 0% { transform: translateY(0) scale(0.4); opacity: 1; } 100% { transform: translateY(-100px) scale(1.2); opacity: 0; } }

        /* КОНТЕНТ */
        .content { flex: 1; padding: 15px; overflow-y: auto; background: rgba(10, 18, 14, 0.85); backdrop-filter: blur(5px); z-index: 20; }
        .section-title { font-size: 18px; font-weight: 900; margin-bottom: 15px; color: #fff; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 15px; padding: 12px; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .card-icon { font-size: 32px; margin-bottom: 6px; }
        .card-title { font-size: 14px; font-weight: 900; margin-bottom: 4px; }
        .card-desc { font-size: 11px; color: #8892b0; margin-bottom: 8px; }
        .card-price { background: rgba(0,0,0,0.5); padding: 8px; border-radius: 8px; font-size: 12px; font-weight: 900; width: 100%; color: #ffd700; border: 1px solid rgba(255,215,0,0.3); cursor: pointer; }
        .card-price:disabled { color: #555; border-color: #333; cursor: not-allowed; }
        .card-price.owned { background: rgba(76, 175, 80, 0.2); color: #4caf50; border-color: #4caf50; }

        /* ДРУЗЬЯ */
        .friend-list { display: flex; flex-direction: column; gap: 10px; margin-top: 15px; }
        .friend-item { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.05); padding: 10px 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); cursor: pointer; }
        .friend-info { display: flex; align-items: center; gap: 10px; width: 100%; }
        .friend-avatar { width: 35px; height: 35px; border-radius: 50%; background: #333; display: flex; justify-content: center; align-items: center; overflow: hidden; }
        .friend-avatar img { width: 100%; height: 100%; object-fit: cover; }
        
        .friend-name-box { display: flex; flex-direction: column; flex: 1; }
        .friend-name-row { display: flex; align-items: center; gap: 6px; font-weight: 900; font-size: 14px; }
        .friend-sub { font-size: 11px; color: #aaa; display: flex; align-items: center; gap: 5px; }
        
        .verified-badge { display: inline-flex; justify-content: center; align-items: center; width: 16px; height: 16px; background: #2196f3; border-radius: 50%; color: #fff; font-size: 10px; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .status-online { background: #4caf50; box-shadow: 0 0 5px #4caf50; }
        .status-offline { background: #555; }

        .tabs-sub { display: flex; gap: 10px; margin-bottom: 15px; align-items: center; }
        .tab-btn { flex: 1; background: rgba(255,255,255,0.1); border: none; color: #aaa; padding: 8px; border-radius: 8px; font-weight: 900; cursor: pointer; }
        .tab-btn.active { background: #4caf50; color: #fff; }

        .leaderboard-item { display: flex; justify-content: space-between; padding: 10px 15px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 14px; cursor: pointer; align-items: center; }
        .lb-rank { font-weight: 900; color: #ffd700; width: 25px; }
        .lb-avatar { width: 30px; height: 30px; border-radius: 50%; margin-right: 10px; overflow: hidden; }
        .lb-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .lb-name { flex: 1; display: flex; align-items: center; gap: 5px; }
        .lb-coins { color: #ffd700; font-weight: 900; }

        /* НАВИГАЦИЯ */
        .bottom-nav { background: rgba(10, 18, 14, 0.98); border-top: 1px solid rgba(46, 125, 50, 0.4); padding: 8px 5px 22px 5px; display: flex; justify-content: space-around; z-index: 30; position: relative; }
        .nav-btn { display: flex; flex-direction: column; align-items: center; background: none; border: none; color: #666; font-size: 9px; font-weight: 900; cursor: pointer; width: 16.6%; transition: 0.2s; }
        .nav-btn.active { color: #81c784; }
        .nav-btn span { font-size: 22px; margin-bottom: 2px; filter: grayscale(1); transition: 0.2s; }
        .nav-btn.active span { filter: drop-shadow(0 0 6px #81c784) grayscale(0); }

        /* МИНИ-ИГРЫ */
        .game-area-mini { height: 300px; width: 100%; background: #112217; position: relative; overflow: hidden; border-radius: 15px; border: 2px solid #4caf50; margin-bottom: 15px; box-shadow: inset 0 0 30px rgba(0,0,0,0.8); }
        .falling-item { position: absolute; font-size: 35px; cursor: pointer; animation: fall linear forwards; }
        @keyframes fall { 0% { transform: translateY(-50px) rotate(0deg); } 100% { transform: translateY(350px) rotate(360deg); } }

        /* МОДАЛКИ */
        .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 1000; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; backdrop-filter: blur(5px); }
        .modal.active { display: flex; }
        .modal-box { background: #1a2e22; border: 2px solid #4caf50; border-radius: 20px; padding: 25px; width: 90%; max-width: 350px; position: relative; }
        
        .name-input { width: 100%; padding: 10px; border-radius: 8px; border: none; font-size: 16px; font-weight: 900; text-align: center; margin-bottom: 15px; background: #fff; color: #111; }

        /* ПРОФИЛЬ */
        .profile-card { background: rgba(0,0,0,0.6); border-radius: 15px; padding: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; position: relative; overflow: hidden; display: flex; flex-direction: column; align-items: center; }
        .profile-bg { position: absolute; inset: 0; z-index: 0; opacity: 0.3; background-size: cover; background-position: center; }
        
        .profile-avatar-large { width: 80px; height: 80px; border-radius: 50%; background: #333; display: flex; justify-content: center; align-items: center; font-size: 40px; position: relative; overflow: hidden; border: 2px solid #fff; z-index: 2;}
        .profile-avatar-large img { width: 100%; height: 100%; object-fit: cover; }
        .profile-frame-wrap { position: relative; width: 90px; height: 90px; display: flex; justify-content: center; align-items: center; margin-bottom: 10px; z-index: 2;}
        .profile-name { font-size: 22px; font-weight: 900; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; z-index: 2;}
        .profile-stats { display: flex; justify-content: center; gap: 20px; margin-top: 15px; font-size: 12px; color: #aaa; width: 100%; z-index: 2;}
        .profile-stats span { font-weight: 900; color: #fff; display: block; font-size: 16px; }
        
        .inventory-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 10px; margin-bottom: 20px; }
        .inv-item { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; text-align: center; border: 2px solid transparent; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .inv-item.selected { border-color: #4caf50; background: rgba(76, 175, 80, 0.2); box-shadow: 0 0 10px #4caf50; }
        .inv-icon { font-size: 24px; margin-bottom: 5px; filter: grayscale(1); }
        .inv-item.owned .inv-icon { filter: none; }

        /* КРАСИВЫЕ ЭМОДЗИ-МЕДАЛИ */
        .medal-emoji { font-size: 18px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5)); }
        .medal-emoji.small { font-size: 12px; }
        .medal-emoji.large { font-size: 28px; }

        /* КОЛЕСО */
        .wheel-container { width: 240px; height: 240px; position: relative; margin: 20px auto; }
        .wheel-pointer { position: absolute; top: -15px; left: 50%; transform: translateX(-50%); font-size: 40px; z-index: 10; text-shadow: 0 2px 5px #000; }
        .wheel { width: 100%; height: 100%; border-radius: 50%; border: 6px solid #ffd700; box-shadow: 0 0 20px rgba(255,215,0,0.4); transition: transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99); overflow: hidden; position: relative; }
        .wheel-segment { position: absolute; top: 0; left: 50%; width: 50%; height: 50%; transform-origin: 0% 100%; clip-path: polygon(0 0, 100% 0, 0 100%); display: flex; align-items: flex-start; justify-content: flex-end; padding: 20px 10px; font-weight: 900; color: #fff; text-shadow: 1px 1px 2px #000; font-size: 14px; }
        .seg-1 { background: #e53935; transform: rotate(0deg) skewY(-30deg); }
        .seg-2 { background: #1e88e5; transform: rotate(60deg) skewY(-30deg); }
        .seg-3 { background: #43a047; transform: rotate(120deg) skewY(-30deg); }
        .seg-4 { background: #fdd835; transform: rotate(180deg) skewY(-30deg); color: #333; text-shadow: none; }
        .seg-5 { background: #8e24aa; transform: rotate(240deg) skewY(-30deg); }
        .seg-6 { background: #fb8c00; transform: rotate(300deg) skewY(-30deg); }

        /* ДУЭТ */
        .duo-area { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; }
        .duo-pandas { display: flex; gap: 30px; align-items: flex-end; justify-content: center; width: 100%; }
        .duo-panda-item { text-align: center; position: relative; }
        .duo-name { font-size: 14px; font-weight: 900; margin-top: 10px; }
        .duo-medal { position: absolute; top: -25px; left: 50%; transform: translateX(-50%); }
        .sad-panda { animation: sadFloat 3s infinite ease-in-out; }
        @keyframes sadFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }

        /* ИСТОРИЯ ПОДАРКОВ */
        .gift-history-item { display: flex; align-items: center; gap: 10px; background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 8px; margin-bottom: 5px; font-size: 12px; text-align: left; }
        .gift-history-icon { font-size: 20px; }

        #error-log { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255,0,0,0.9); color: white; padding: 10px; font-size: 12px; z-index: 9999; display: none; word-break: break-all; }
        #loading { position: fixed; inset: 0; background: #0a120e; z-index: 10000; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 20px; font-weight: 900; color: #4caf50; }
    </style>
</head>
<body>
    <div id="loading"><div>Загрузка игры...</div><div id="loading-text" style="font-size:12px; margin-top:10px;">Подключение...</div></div>

    <div id="setup-screen">
        <h1>Кто у тебя появится?</h1>
        <p>Выбери пол своего питомца.</p>
        <div class="gender-btns">
            <div class="gender-btn" onclick="selectGender('male')"><span class="icon">👦</span>Мальчик</div>
            <div class="gender-btn" onclick="selectGender('female')"><span class="icon">👧</span>Девочка</div>
        </div>
    </div>

    <!-- МОДАЛКИ -->
    <div class="modal" id="name-modal"><div class="modal-box"><h2 style="color:#4caf50; margin-bottom:15px;">Никнейм</h2><input type="text" id="name-input" class="name-input" maxlength="15"><button class="card-price" style="background:#4caf50; color:#fff;" onclick="saveName()">Сохранить</button><button class="card-price" style="background:#555; color:#fff; margin-top:10px;" onclick="closeModal('name-modal')">Отмена</button></div></div>

    <div class="modal" id="gift-modal">
        <div class="modal-box">
            <h2 style="color:#ffd700; margin-bottom:15px;">Подарить игроку</h2>
            <div style="display:flex; justify-content:space-around; margin-bottom:20px;">
                <div onclick="sendGift('🌹', 10)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">🌹</div><div style="font-size:10px; color:#00e5ff;">10 💎</div></div>
                <div onclick="sendGift('🎂', 50)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">🎂</div><div style="font-size:10px; color:#00e5ff;">50 💎</div></div>
                <div onclick="sendGift('🧸', 100)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">🧸</div><div style="font-size:10px; color:#00e5ff;">100 💎</div></div>
                <div onclick="sendGift('👑', 500)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">👑</div><div style="font-size:10px; color:#00e5ff;">500 💎</div></div>
            </div>
            <button class="card-price" style="background:#555; color:#fff;" onclick="closeModal('gift-modal')">Отмена</button>
        </div>
    </div>

    <div class="modal" id="view-profile-modal">
        <div class="modal-box" style="text-align:center;">
            <div class="profile-frame-wrap" style="margin:0 auto 10px;">
                <div class="avatar-frame" id="vp-frame" style="inset:0;"></div>
                <div class="profile-avatar-large" id="vp-avatar">🐼</div>
            </div>
            <div class="profile-name" id="vp-name">Ник</div>
            <div class="medal-emoji large" id="vp-medal" style="display:none; margin:0 auto 10px;"></div>
            
            <div class="profile-stats" style="justify-content:space-around; margin-bottom:15px;">
                <div>Монеты <span id="vp-coins">0</span></div>
                <div>Подарки <span id="vp-gifts">0</span></div>
            </div>

            <div style="text-align:left; margin-bottom:15px;">
                <div style="font-weight:900; margin-bottom:5px; color:#ffd700;">История подарков:</div>
                <div id="vp-gift-history" style="max-height:100px; overflow-y:auto;"></div>
            </div>

            <button class="card-price" style="background:#ff9800; color:#fff; margin-top:15px;" onclick="openGiftModal()">Подарить 🎁</button>
            <button class="card-price" style="background:#555; color:#fff; margin-top:10px;" onclick="closeModal('view-profile-modal')">Закрыть</button>
        </div>
    </div>

    <div class="modal" id="wheel-modal">
        <div class="modal-box" style="text-align:center;">
            <h2 style="color:#ffd700; margin-bottom:15px;">🎡 Колесо Фортуны</h2>
            <div class="wheel-container">
                <div class="wheel-pointer">▼</div>
                <div class="wheel" id="wheel-icon">
                    <div class="wheel-segment seg-1">100</div>
                    <div class="wheel-segment seg-2">500</div>
                    <div class="wheel-segment seg-3">1000</div>
                    <div class="wheel-segment seg-4">5000</div>
                    <div class="wheel-segment seg-5">10000</div>
                    <div class="wheel-segment seg-6">50000</div>
                </div>
            </div>
            <button class="card-price" style="background:#4caf50; color:#fff; padding:15px; margin-top:20px;" onclick="spinWheel()">Крутить</button>
        </div>
    </div>

    <div class="modal" id="chest-modal"><div class="modal-box" style="text-align:center;"><h2 style="color:#ffd700;">🎁 Сундук дня!</h2><div style="font-size: 60px; margin: 20px 0;">📦</div><button class="card-price" style="background:#4caf50; color:#fff; padding:15px;" onclick="claimChest()">Открыть</button></div></div>

    <!-- ФОН -->
    <div class="bg-container" id="bg-container">
        <div class="bg-sky"><div class="bg-moon"></div><div class="bg-clouds"></div></div>
        <div class="bg-mountains"><svg viewBox="0 0 400 200" preserveAspectRatio="none"><path d="M0,200 L50,80 L120,120 L180,40 L260,90 L340,60 L400,150 L400,200 Z" fill="#1e293b"/><path d="M0,200 L70,110 L150,150 L240,80 L320,130 L400,200 Z" fill="#334155"/></svg></div>
        <div class="bg-bamboo"><div class="stalk" style="height: 70%; left: 5%;"></div><div class="stalk" style="height: 90%; left: 20%;"></div><div class="stalk" style="height: 60%; right: 15%;"></div><div class="stalk" style="height: 80%; right: 5%;"></div></div>
        <div class="bg-ground"></div>
    </div>

    <!-- ХЕДЕР -->
    <div class="header">
        <div class="user-info-block">
            <div class="avatar-wrap" onclick="goToProfile()">
                <div class="avatar-frame default" id="header-frame"></div>
                <div class="profile-avatar-mini" id="mini-avatar"><span>🐼</span></div>
            </div>
            <div>
                <div class="name-medal-block" onclick="goToProfile()">
                    <div class="name-row">
                        <span class="header-nick nick-default" id="my-name">Ник</span>
                        <div class="header-medal" id="header-medal" style="display:none;"></div>
                    </div>
                    <div class="streak-badge" id="streak-badge">🔥 Серия: 0</div>
                </div>
                <div class="res-row">
                    <div class="coins-box"><span id="coins">0</span> <span class="icon-coin">$</span></div>
                    <div class="gems-box" onclick="goToGemShop()"><span id="gems">0</span> <span class="icon-gem">💎</span></div>
                </div>
            </div>
        </div>
        <div class="energy-box" onclick="tg.showAlert('Энергия восстанавливается со временем.')">
            <div class="energy-text"><span id="energy">1000</span>/<span id="max-energy">1000</span> ⚡</div>
            <div class="energy-bar"><div class="energy-fill" id="energy-fill"></div></div>
            <div style="font-size:10px; color:#fff; margin-top:5px;" id="conn-status">Подключение...</div>
        </div>
    </div>

    <!-- ЭКРАНЫ -->
    <div class="screens">
        <!-- ТАП -->
        <div class="screen active" id="screen-tap">
            <div class="tap-area">
                <div style="text-align: center; position: relative;">
                    <div class="panda-wrapper" id="panda-wrapper">
                        <svg viewBox="0 0 200 220" style="width:100%; height:100%; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5));">
                            <defs>
                                <radialGradient id="bodyGrad" cx="40%" cy="30%" r="80%"><stop offset="0%" stop-color="#ffffff" /><stop offset="60%" stop-color="#f5f5f5" /><stop offset="100%" stop-color="#d0d0d0" /></radialGradient>
                                <radialGradient id="bellyGrad" cx="50%" cy="40%" r="60%"><stop offset="0%" stop-color="#ffffff" /><stop offset="100%" stop-color="#ececec" /></radialGradient>
                                <radialGradient id="shadowGrad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#000" stop-opacity="0.35" /><stop offset="100%" stop-color="#000" stop-opacity="0" /></radialGradient>
                                <radialGradient id="padGrad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#ffb6c1"/><stop offset="100%" stop-color="#ff69b4"/></radialGradient>
                            </defs>
                            <ellipse cx="100" cy="205" rx="75" ry="15" fill="url(#shadowGrad)" />
                            <g class="panda-root">
                                <g class="hind-legs"><ellipse cx="55" cy="175" rx="24" ry="18" fill="#1a1a1a" /><ellipse cx="145" cy="175" rx="24" ry="18" fill="#1a1a1a" /></g>
                                <g class="body">
                                    <ellipse cx="100" cy="140" rx="62" ry="55" fill="url(#bodyGrad)" />
                                    <path class="belly-normal" d="M 55 160 Q 100 130 145 160 Q 135 195 100 198 Q 65 195 55 160 Z" fill="url(#bellyGrad)" />
                                    <path class="belly-pregnant" d="M 40 160 Q 100 110 160 160 Q 150 205 100 208 Q 50 205 40 160 Z" fill="url(#bellyGrad)" style="display:none;" />
                                </g>
                                <g class="head" transform="translate(0, -5)">
                                    <g id="ear-left"><circle cx="45" cy="45" r="20" fill="#1a1a1a" /><circle cx="45" cy="45" r="10" fill="#333" /></g>
                                    <g id="ear-right"><circle cx="155" cy="45" r="20" fill="#1a1a1a" /><circle cx="155" cy="45" r="10" fill="#333" /></g>
                                    <ellipse cx="100" cy="90" rx="65" ry="58" fill="url(#bodyGrad)" />
                                    <ellipse cx="70" cy="85" rx="18" ry="23" fill="#111" /><ellipse cx="130" cy="85" rx="18" ry="23" fill="#111" />
                                    <g class="eye" id="eye-L"><circle cx="70" cy="85" r="9" fill="#fff" /><circle cx="70" cy="85" r="6" fill="#111" /><circle cx="67.5" cy="82.5" r="2.5" fill="#fff" /></g>
                                    <g class="eye" id="eye-R"><circle cx="130" cy="85" r="9" fill="#fff" /><circle cx="130" cy="85" r="6" fill="#111" /><circle cx="127.5" cy="82.5" r="2.5" fill="#fff" /></g>
                                    <g id="gender-features"></g>
                                    <ellipse cx="100" cy="105" rx="8" ry="5" fill="#111" />
                                    <path id="mouth-path" d="M 92 112 Q 100 118 108 112" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round" />
                                    <g id="gender-bow" style="display:none;"><path d="M 120 30 L 140 20 L 140 40 Z" fill="#ff69b4" /><path d="M 150 30 L 170 20 L 170 40 Z" fill="#ff69b4" /><circle cx="145" cy="30" r="6" fill="#ff1493" /></g>
                                </g>
                                <g class="front-legs">
                                    <g class="hand-left"><ellipse cx="45" cy="145" rx="18" ry="22" fill="#1a1a1a" /><ellipse cx="38" cy="160" rx="6" ry="5" fill="url(#padGrad)" /><ellipse cx="48" cy="162" rx="6" ry="5" fill="url(#padGrad)" /></g>
                                    <g class="hand-right"><ellipse cx="155" cy="145" rx="18" ry="22" fill="#1a1a1a" /><ellipse cx="152" cy="162" rx="6" ry="5" fill="url(#padGrad)" /><ellipse cx="162" cy="160" rx="6" ry="5" fill="url(#padGrad)" /></g>
                                </g>
                            </g>
                        </svg>
                    </div>
                    <!-- ПИТОМЕЦ (Полноценный SVG) -->
                    <div class="pet-container" id="my-pet-container" style="display:none;">
                        <svg class="pet-svg" viewBox="0 0 100 100" style="width:100%; height:100%;">
                            <g id="my-pet-icon"></g>
                        </svg>
                    </div>
                </div>
            </div>
        </div>

        <!-- ПРОФИЛЬ -->
        <div class="screen" id="screen-profile">
            <div class="content">
                <div class="profile-card">
                    <div class="profile-bg" id="profile-bg"></div>
                    <div class="profile-frame-wrap">
                        <div class="avatar-frame default" id="profile-frame"></div>
                        <div class="profile-avatar-large" id="my-avatar-large">🐼</div>
                    </div>
                    <div class="profile-name" id="my-name-profile">Загрузка...</div>
                    <div class="medal-emoji large" id="my-medal-display" style="display:none; margin:0 auto 10px;"></div>
                    <button class="card-price" style="width:auto; display:inline-block; margin-top:5px; background:#2196f3; padding:5px 15px;" onclick="openNameModal()">Изменить ник</button>
                    
                    <div class="profile-stats">
                        <div>Монеты <span id="stat-coins">0</span></div>
                        <div>Гемы <span id="stat-gems">0</span></div>
                        <div>Серия <span id="stat-streak">0</span></div>
                    </div>
                </div>

                <div class="section-title">Стиль ника</div>
                <div class="inventory-grid" id="anims-grid"></div>

                <div class="section-title">Мои медали</div>
                <div class="inventory-grid" id="medals-grid"></div>

                <div class="section-title">Мои рамки</div>
                <div class="inventory-grid" id="frames-grid"></div>
                
                <div id="gifts-list" style="font-size:14px; color:#aaa; text-align:center; margin-top:20px;">Подарков пока нет</div>
            </div>
        </div>

        <!-- ФЕРМА -->
        <div class="screen" id="screen-farm">
            <div class="content"><div class="section-title">Ферма бамбука 🎋</div><div class="grid" id="farm-grid"></div></div>
        </div>

        <!-- ДРУЗЬЯ -->
        <div class="screen" id="screen-friends">
            <div class="content">
                <div class="section-title">Друзья 👥</div>
                <div class="tabs-sub">
                    <button class="tab-btn active" onclick="switchFriendsTab('list', this)">Друзья</button>
                    <button class="tab-btn" onclick="switchFriendsTab('top', this)">Топ 50</button>
                </div>
                <div id="friends-list-container">
                    <button class="card-price" onclick="inviteFriend()" style="margin-bottom:10px; background:#2196f3; color:#fff; border:none;">Пригласить друга</button>
                    <div class="friend-list" id="friends-list"><p style="text-align:center; color:#888;">Загрузка...</p></div>
                </div>
                <div id="leaderboard-container" style="display:none;"><div id="leaderboard-list"></div></div>
            </div>
        </div>

        <!-- МАГАЗИН -->
        <div class="screen" id="screen-shop">
            <div class="content">
                <div class="section-title">Магазин 🛍️</div>
                <div class="tabs-sub" style="margin-bottom:15px;">
                    <button class="tab-btn active" onclick="switchShopTab('items', this)">Питомцы</button>
                    <button class="tab-btn" onclick="switchShopTab('gems', this)">Гемы 💎</button>
                </div>
                <div class="grid" id="shop-grid"></div>
                <div class="grid" id="gems-grid" style="display:none;">
                    <div class="card"><div class="card-icon">💎</div><div class="card-title">100 Гемов</div><button class="card-price" onclick="buyGems(50)">50 ⭐</button></div>
                    <div class="card"><div class="card-icon">💎</div><div class="card-title">500 Гемов</div><button class="card-price" onclick="buyGems(200)">200 ⭐</button></div>
                    <div class="card"><div class="card-icon">💎</div><div class="card-title">1000 Гемов</div><button class="card-price" onclick="buyGems(350)">350 ⭐</button></div>
                    <div class="card"><div class="card-icon">💎</div><div class="card-title">5000 Гемов</div><button class="card-price" onclick="buyGems(1500)">1500 ⭐</button></div>
                    <div class="card"><div class="card-icon">💎</div><div class="card-title">10000 Гемов</div><button class="card-price" onclick="buyGems(2500)">2500 ⭐</button></div>
                </div>
            </div>
        </div>

        <!-- ИГРЫ -->
        <div class="screen" id="screen-games">
            <div class="content">
                <div class="section-title">Мини-игры 🏆</div>
                <div class="game-area-mini" id="game-area-mini"></div>
                <div style="text-align:center; font-size:24px; font-weight:900; margin-bottom:10px;">Счет: <span id="mini-score">0</span></div>
                <button class="card-price" id="mini-btn-bamboo" onclick="startMiniGame()" style="background:#4caf50; color:#fff; padding:15px; margin-bottom:10px;">Поймай бамбук 🎋</button>
                <button class="card-price" onclick="document.getElementById('wheel-modal').classList.add('active')" style="background:#9c27b0; color:#fff; padding:15px;">Колесо Фортуны 🎡</button>
            </div>
        </div>

        <!-- ДУЭТ -->
        <div class="screen" id="screen-family">
            <div class="content" style="display:flex; flex-direction:column;">
                <div class="section-title">Дуэт 👨‍👩‍👧‍👦</div>
                
                <div class="duo-area" id="duo-area-solo">
                    <div class="sad-panda" style="font-size:80px; text-align:center; margin:20px 0;">🐼</div>
                    <p style="color:#aaa; margin-bottom:20px;">Ты пока один. Пригласи друга, чтобы играть вместе!</p>
                    <button class="card-price" onclick="inviteFriend()" style="background:#2196f3; color:#fff; padding:15px; width:80%; border:none; margin:0 auto;">Пригласить друга</button>
                </div>

                <div class="duo-area" id="duo-area-active" style="display:none;">
                    <div class="duo-pandas">
                        <div class="duo-panda-item">
                            <div class="duo-medal" id="duo-my-medal"></div>
                            <div style="font-size:60px;">🐼</div>
                            <div class="duo-name" id="duo-my-name">Ты</div>
                        </div>
                        <div class="duo-panda-item">
                            <div class="duo-medal" id="duo-partner-medal"></div>
                            <div style="font-size:60px;">🐼</div>
                            <div class="duo-name" id="duo-partner-name">Друг</div>
                        </div>
                    </div>
                    <div class="card" style="margin-top:20px; width:80%;">
                        <div id="family-status" style="font-size:16px; font-weight:900; color:#ffd700; margin-bottom:10px;">Вы вместе!</div>
                        <div id="pregnancy-btn-container"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- НАВИГАЦИЯ -->
    <div class="bottom-nav">
        <button class="nav-btn active" onclick="switchTab('tap', this)"><span>👆</span>Панда</button>
        <button class="nav-btn" onclick="switchTab('friends', this)"><span>👥</span>Друзья</button>
        <button class="nav-btn" onclick="switchTab('farm', this)"><span>🌱</span>Ферма</button>
        <button class="nav-btn" onclick="switchTab('shop', this)"><span>🛍️</span>Магазин</button>
        <button class="nav-btn" onclick="switchTab('games', this)"><span>🎮</span>Игры</button>
        <button class="nav-btn" onclick="switchTab('profile', this)"><span>👤</span>Профиль</button>
    </div>

    <div id="error-log"></div>

    <script>
        let eyeTimeout = null; 

        setTimeout(() => { document.getElementById('loading-text').innerText = "Сервер просыпается..."; }, 4000);
        setTimeout(() => { document.getElementById('loading').style.display = 'none'; }, 500);

        window.onerror = function(msg, url, line) {
            if (msg.includes("Script error") || msg.includes("NetworkError") || msg.includes("Failed to fetch")) return true; 
            document.getElementById('error-log').style.display = 'block';
            document.getElementById('error-log').innerText = "Ошибка: " + msg + " | Строка: " + line;
            return false;
        };

        const tg = window.Telegram.WebApp;
        tg.expand();

        let state = {
            coins: 500, gems: 0, gender: null, streakDays: 1, lastLogin: 0, accountCreated: Date.now(),
            tapPower: 1, energy: 1000, maxEnergy: 1000, regen: 5,
            isPregnant: false, pregnancyEnd: 0, hasBaby: false,
            inventory: { pet_dog: false, pet_cat: false, pet_fox: false, pet_dragon: false },
            equipped: { pet: 'none' },
            bamboos: [{ id: 1, stage: 0, planted: 0 }, { id: 2, stage: 0, planted: 0 }, { id: 3, stage: 0, planted: 0 }],
            lastMiniGame: 0, lastChest: 0, lastWheel: 0,
            friends: [], giftsReceived: 0, giftHistory: [],
            nickname: '', selectedMedal: 'none', selectedFrame: 'default', selectedNickAnim: 'default', avatarUrl: '',
            unlockedMedals: [], unlockedFrames: [], unlockedAnims: []
        };

        const urlParams = new URLSearchParams(window.location.search);
        const startParam = tg.initDataUnsafe?.start_param; // ID пригласившего друга
        const myId = String(tg.initDataUnsafe?.user?.id || Math.floor(Math.random() * 10000));
        const roomId = startParam || myId; 
        
        const WS_URL = window.location.origin.replace('https://', 'wss://'); 
        const API_URL = window.location.origin;
        let ws;
        let currentMode = 'solo';
        let inviterId = startParam && startParam !== myId ? startParam : null;

        // ========== АДМИН РЕЖИМ ==========
        const ADMIN_ID = '6877882967'; 
        if (myId === ADMIN_ID) {
            state.coins = 99999999; state.gems = 999999; state.streakDays = 730; state.isAdmin = true; state.verified = true;
            state.inventory = { pet_dog: true, pet_cat: true, pet_fox: true, pet_dragon: true }; state.equipped = { pet: 'pet_dragon' };
            state.selectedMedal = 'mythic'; state.selectedFrame = 'legend'; state.selectedNickAnim = 'rainbow';
        }

        // ========== КОНФИГ ==========
        const allMedals = [
            { id: 'bronze', name: 'Бронза', req: 30, emoji: '🥉' }, 
            { id: 'silver', name: 'Серебро', req: 90, emoji: '🥈' },
            { id: 'gold', name: 'Золото', req: 180, emoji: '🥇' }, 
            { id: 'epic', name: 'Эпик', req: 365, emoji: '💎' },
            { id: 'mythic', name: 'Мифик', req: 730, emoji: '👑' }
        ];
        const allFrames = [
            { id: 'default', name: 'Новичок', cssClass: 'default' }, 
            { id: 'millionaire', name: 'Богач', cssClass: 'millionaire' },
            { id: 'legend', name: 'Легенда', cssClass: 'legend' }
        ];
        const allAnims = [
            { id: 'default', name: 'Обычный', cssClass: 'nick-default' }, 
            { id: 'gold', name: 'Золото', cssClass: 'nick-gold' },
            { id: 'fire', name: 'Огонь', cssClass: 'nick-fire' }, 
            { id: 'rainbow', name: 'Радуга', cssClass: 'nick-rainbow' }
        ];

        // КРАСИВЫЕ ПОЛНОЦЕННЫЕ SVG ПИТОМЦЫ
        const petsData = {
            'pet_dog': { name: 'Собачка', svg: '<path d="M20,80 Q10,60 20,40 L30,40 Q30,20 40,20 Q50,20 50,40 L70,40 Q70,20 80,20 Q90,20 90,40 L100,40 Q110,60 100,80 Z" fill="#e6a869"/><circle cx="40" cy="50" r="5" fill="#fff"/><circle cx="60" cy="50" r="5" fill="#fff"/><circle cx="40" cy="50" r="2" fill="#000"/><circle cx="60" cy="50" r="2" fill="#000"/><ellipse cx="50" cy="60" rx="8" ry="5" fill="#000"/><path d="M50,65 Q50,70 55,70 Q60,70 60,65" fill="none" stroke="#000" stroke-width="2"/>' },
            'pet_cat': { name: 'Котик', svg: '<circle cx="50" cy="50" r="30" fill="#ffb74d"/><polygon points="20,20 30,45 15,45" fill="#ffb74d"/><polygon points="80,20 70,45 85,45" fill="#ffb74d"/><circle cx="35" cy="45" r="5" fill="#fff"/><circle cx="65" cy="45" r="5" fill="#fff"/><circle cx="35" cy="45" r="2" fill="#000"/><circle cx="65" cy="45" r="2" fill="#000"/><ellipse cx="50" cy="55" rx="6" ry="4" fill="#ff9999"/><path d="M40,60 Q50,70 60,60" fill="none" stroke="#000" stroke-width="2"/>' },
            'pet_fox': { name: 'Лисичка', svg: '<path d="M20,80 L10,40 L35,45 L50,20 L65,45 L90,40 L80,80 Z" fill="#ff7043"/><circle cx="35" cy="55" r="5" fill="#fff"/><circle cx="65" cy="55" r="5" fill="#fff"/><circle cx="35" cy="55" r="2" fill="#000"/><circle cx="65" cy="55" r="2" fill="#000"/><ellipse cx="50" cy="65" rx="6" ry="4" fill="#000"/>' },
            'pet_dragon': { name: 'Дракон', svg: '<circle cx="50" cy="50" r="30" fill="#4caf50"/><path d="M20,40 Q30,20 40,40 Q50,20 60,40 Q70,20 80,40" fill="none" stroke="#81c784" stroke-width="5"/><circle cx="35" cy="45" r="5" fill="#fff"/><circle cx="65" cy="45" r="5" fill="#fff"/><circle cx="35" cy="45" r="2" fill="#000"/><circle cx="65" cy="45" r="2" fill="#000"/><path d="M40,60 Q50,70 60,60" fill="none" stroke="#000" stroke-width="2"/>' }
        };

        if (!state.avatarUrl) state.avatarUrl = tg.initDataUnsafe?.user?.photo_url || '';
        
        function updateAvatarUI() {
            const miniAv = document.getElementById('mini-avatar'); const largeAv = document.getElementById('my-avatar-large');
            if (state.avatarUrl) { miniAv.innerHTML = `<img src="${state.avatarUrl}">`; largeAv.innerHTML = `<img src="${state.avatarUrl}">`; } 
            else { miniAv.innerHTML = '🐼'; largeAv.innerHTML = '🐼'; }
        }

        function goToProfile() { switchTab('profile', document.querySelectorAll('.nav-btn')[5]); }
        function goToGemShop() { switchTab('shop', document.querySelectorAll('.nav-btn')[3]); switchShopTab('gems', document.querySelectorAll('#screen-shop .tab-btn')[1]); }

        function openNameModal() { document.getElementById('name-input').value = state.nickname; document.getElementById('name-modal').classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }
        function saveName() {
            let n = document.getElementById('name-input').value.trim();
            if (n === '') n = `Panda_${myId.substring(0,4)}`; if (n.length > 15) n = n.substring(0, 15);
            state.nickname = n;
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "set_name", name: n }));
            closeModal('name-modal'); updateUI();
        }

        function checkUnlocks() {
            if (!state.unlockedMedals) state.unlockedMedals = [];
            if (!state.unlockedFrames) state.unlockedFrames = [];
            if (!state.unlockedAnims) state.unlockedAnims = [];

            if (state.isAdmin) {
                state.unlockedMedals = allMedals.map(m => m.id); state.unlockedFrames = allFrames.map(f => f.id); state.unlockedAnims = allAnims.map(a => a.id);
            } else {
                const d = Math.floor((Date.now() - state.accountCreated) / (1000 * 60 * 60 * 24));
                state.unlockedMedals = allMedals.filter(m => d >= m.req).map(m => m.id);
                state.unlockedFrames = ['default']; if (state.coins >= 1000000) state.unlockedFrames.push('millionaire'); if (state.streakDays >= 365) state.unlockedFrames.push('legend');
                state.unlockedAnims = ['default']; if (state.streakDays >= 30) state.unlockedAnims.push('gold'); if (state.streakDays >= 180) state.unlockedAnims.push('fire'); if (state.streakDays >= 365) state.unlockedAnims.push('rainbow');
            }
        }

        function equip(type, id) {
            if (type === 'Medal' && state.unlockedMedals.includes(id)) state.selectedMedal = id;
            if (type === 'Frame' && state.unlockedFrames.includes(id)) state.selectedFrame = id;
            if (type === 'NickAnim' && state.unlockedAnims.includes(id)) state.selectedNickAnim = id;
            updateUI();
        }

        function renderProfile() {
            const frame = allFrames.find(f => f.id === state.selectedFrame)?.cssClass || 'default';
            const animCss = allAnims.find(a => a.id === state.selectedNickAnim)?.cssClass || 'nick-default';
            const med = allMedals.find(m => m.id === state.selectedMedal);

            // Header
            const hFrame = document.getElementById('header-frame'); if(hFrame) hFrame.className = `avatar-frame ${frame}`;
            const nameEl = document.getElementById('my-name');
            if(nameEl) { nameEl.className = `header-nick ${animCss}`; nameEl.innerText = state.nickname; }
            
            const hMed = document.getElementById('header-medal');
            if(hMed) {
                if (med) { hMed.style.display = 'inline-flex'; hMed.innerText = med.emoji; }
                else hMed.style.display = 'none';
            }

            // Profile Page
            const pFrame = document.getElementById('profile-frame'); if(pFrame) pFrame.className = `avatar-frame ${frame}`;
            const profName = document.getElementById('my-name-profile');
            if(profName) { profName.className = `profile-name ${animCss}`; profName.innerText = state.nickname; }
            
            const pMed = document.getElementById('my-medal-display');
            if(pMed) {
                if (med) { pMed.style.display = 'block'; pMed.innerText = med.emoji; }
                else pMed.style.display = 'none';
            }

            // Динамический фон профиля
            const bgElem = document.getElementById('profile-bg');
            if(bgElem) {
                const hue = parseInt(myId) % 360;
                bgElem.style.backgroundImage = `linear-gradient(135deg, hsl(${hue}, 70%, 40%), hsl(${(hue+60)%360}, 70%, 20%))`;
            }

            // Pet
            const petEl = document.getElementById('my-pet-container');
            const petIcon = document.getElementById('my-pet-icon');
            if (petEl && petIcon) {
                if (state.equipped.pet && state.equipped.pet !== 'none') {
                    petEl.style.display = 'flex';
                    petIcon.innerHTML = petsData[state.equipped.pet].svg;
                } else {
                    petEl.style.display = 'none';
                }
            }

            // Grids
            const mGrid = document.getElementById('medals-grid'); if(mGrid) { mGrid.innerHTML = '';
                allMedals.forEach(m => { const o = state.unlockedMedals.includes(m.id); const s = state.selectedMedal === m.id; mGrid.innerHTML += `<div class="inv-item ${o?'owned':''} ${s?'selected':''}" onclick="equip('Medal','${m.id}')" style="${o?'':'opacity:0.3;'}"><div class="medal-emoji">${m.emoji}</div><div style="font-size:10px; margin-top:5px;">${m.name}</div></div>`; });
            }
            const fGrid = document.getElementById('frames-grid'); if(fGrid) { fGrid.innerHTML = '';
                allFrames.forEach(f => { const o = state.unlockedFrames.includes(f.id); const s = state.selectedFrame === f.id; fGrid.innerHTML += `<div class="inv-item ${o?'owned':''} ${s?'selected':''}" onclick="equip('Frame','${f.id}')" style="${o?'':'opacity:0.3;'}"><div class="inv-icon" style="border:4px solid #fff; border-radius:50%; width:30px; height:30px; margin:0 auto; ${f.id==='millionaire'?'border-color:#ffd700; box-shadow:0 0 10px #ffd700;':f.id==='legend'?'border-color:#00e5ff; box-shadow:0 0 15px #00e5ff;':''}"></div><div style="font-size:10px; margin-top:5px;">${f.name}</div></div>`; });
            }
            const aGrid = document.getElementById('anims-grid'); if(aGrid) { aGrid.innerHTML = '';
                allAnims.forEach(a => { const o = state.unlockedAnims.includes(a.id); const s = state.selectedNickAnim === a.id; aGrid.innerHTML += `<div class="inv-item ${o?'owned':''} ${s?'selected':''}" onclick="equip('NickAnim','${a.id}')" style="${o?'':'opacity:0.3;'}"><div class="inv-icon ${a.cssClass}" style="font-weight:900; font-size:20px;">Aa</div><div style="font-size:10px;">${a.name}</div></div>`; });
            }

            if(document.getElementById('gifts-list')) document.getElementById('gifts-list').innerText = state.giftsReceived > 0 ? `Подарков: ${state.giftsReceived} 🎁` : 'Подарков пока нет';
            if(document.getElementById('stat-coins')) document.getElementById('stat-coins').innerText = state.coins.toLocaleString(); 
            if(document.getElementById('stat-gems')) document.getElementById('stat-gems').innerText = state.gems.toLocaleString(); 
            if(document.getElementById('stat-streak')) document.getElementById('stat-streak').innerText = state.streakDays;
        }

        function renderFarm() {
            const grid = document.getElementById('farm-grid'); if(!grid) return; grid.innerHTML = '';
            state.bamboos.forEach(b => {
                let s = "Пусто", btn = "Посадить", icon = "🟫", dis = false;
                if (b.stage === 1) { 
                    const t = Math.ceil((60000 - (Date.now() - b.planted)) / 1000); 
                    s = t > 0 ? `Растет... ${t}с` : "Созрел!"; 
                    btn = "Ждем"; icon = "🌱"; dis = t > 0; 
                } else if (b.stage === 2) { s = "Созрел!"; btn = "Собрать"; icon = "🎋"; } 
                else if (b.stage === 3) { s = "Сгнил!"; btn = "Убрать"; icon = "🥀"; }
                grid.innerHTML += `<div class="card"><div class="card-icon">${icon}</div><div class="card-title">Участок ${b.id}</div><div class="card-desc">${s}</div><button class="card-price" ${dis ? 'disabled' : ''} onclick="handleFarmClick(${b.id})">${btn}</button></div>`;
            });
        }

        function handleFarmClick(id) {
            const b = state.bamboos.find(x => x.id === id);
            if (b.stage === 0) { b.planted = Date.now(); b.stage = 1; } 
            else if (b.stage === 2) { state.coins += 500; b.stage = 0; tg.showAlert("+500 монет!"); } 
            else if (b.stage === 3) { b.stage = 0; }
            saveGame(); updateUI();
        }

        function switchShopTab(tab, btn) { 
            document.querySelectorAll('#screen-shop .tab-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); 
            document.getElementById('shop-grid').style.display = tab === 'items' ? 'grid' : 'none'; 
            document.getElementById('gems-grid').style.display = tab === 'gems' ? 'grid' : 'none'; 
        }

        function buyGems(amount) { tg.showAlert(`Для покупки ${amount} гемов за Telegram Stars нужно подключить платежную систему в BotFather. Скоро добавим!`); }
        
        function spinWheel() {
            const now = Date.now(); if (now - state.lastWheel < 24 * 60 * 60 * 1000 && !state.isAdmin) { tg.showAlert("Завтра!"); return; }
            state.lastWheel = now;
            const wheel = document.getElementById('wheel-icon');
            const deg = Math.floor(Math.random() * 360) + 1440;
            wheel.style.transform = `rotate(${deg}deg)`;
            setTimeout(() => {
                const win = [100, 500, 1000, 5000, 10000, 50000][Math.floor(Math.random() * 6)];
                state.coins += win; tg.showAlert(`🎉 Выигрыш: ${win} монет!`);
                closeModal('wheel-modal'); updateUI();
            }, 4000);
        }

        let miniActive = false;
        function startMiniGame() {
            if (Date.now() - state.lastMiniGame < 5 * 60 * 1000 && !state.isAdmin) return; state.lastMiniGame = Date.now(); updateUI();
            const area = document.getElementById('game-area-mini'); area.innerHTML = ''; miniActive = true; let score = 0; document.getElementById('mini-score').innerText = score;
            const interval = setInterval(() => {
                if (!miniActive) return;
                const item = document.createElement('div'); item.className = 'falling-item'; item.innerText = ['🎋', '🍎', '🍔'][Math.floor(Math.random()*3)];
                item.style.left = Math.random() * 80 + 10 + '%'; item.style.animationDuration = (Math.random() * 1.5 + 1) + 's';
                item.onclick = () => { if (miniActive) { score++; document.getElementById('mini-score').innerText = score; item.remove(); } };
                area.appendChild(item); setTimeout(() => item.remove(), 2500);
            }, 300);
            setTimeout(() => { miniActive = false; clearInterval(interval); state.coins += score * 100; tg.showAlert(`Игра окончена! +${score * 100} монет.`); updateUI(); }, 10000);
        }

        function updateUI() {
            if(document.getElementById('coins')) document.getElementById('coins').innerText = Math.floor(state.coins).toLocaleString(); 
            if(document.getElementById('gems')) document.getElementById('gems').innerText = Math.floor(state.gems).toLocaleString();
            if(document.getElementById('energy')) document.getElementById('energy').innerText = Math.floor(state.energy); 
            if(document.getElementById('max-energy')) document.getElementById('max-energy').innerText = state.maxEnergy; 
            if(document.getElementById('energy-fill')) document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';
            if(document.getElementById('streak-badge')) document.getElementById('streak-badge').innerText = `🔥 Серия: ${state.streakDays}`;
            
            checkUnlocks(); renderProfile(); renderFarm(); renderShop(); renderDuo();
            
            const bellyNormal = document.querySelector('.belly-normal'); const bellyPregnant = document.querySelector('.belly-pregnant');
            if (bellyNormal && bellyPregnant) {
                if (state.isPregnant) { 
                    bellyNormal.style.display = 'none'; bellyPregnant.style.display = 'block'; 
                    if (Date.now() >= state.pregnancyEnd) { state.isPregnant = false; state.hasBaby = true; bellyNormal.style.display = 'block'; bellyPregnant.style.display = 'none'; tg.showAlert("🎉 Родился малыш!"); } 
                } 
                else { bellyNormal.style.display = 'block'; bellyPregnant.style.display = 'none'; }
            }

            saveGame();
        }

        function saveGame() { localStorage.setItem('pandaUltimate', JSON.stringify(state)); }

        const shopData = [
            { id: 'pet_dog', name: 'Собачка', price: 5000 },
            { id: 'pet_cat', name: 'Котик', price: 15000 },
            { id: 'pet_fox', name: 'Лисичка', price: 50000 },
            { id: 'pet_dragon', name: 'Дракон', price: 150000 }
        ];
        function renderShop() {
            const grid = document.getElementById('shop-grid'); if(!grid) return; grid.innerHTML = '';
            shopData.forEach(item => { 
                const isOwned = state.inventory[item.id]; 
                const isEq = state.equipped.pet === item.id; 
                grid.innerHTML += `<div class="card"><div class="card-icon" style="width:60px; height:60px;"><svg viewBox="0 0 100 100">${petsData[item.id].svg}</svg></div><div class="card-title" style="margin-top:10px;">${item.name}</div><button class="card-price ${isOwned ? (isEq ? 'owned' : '') : ''}" onclick="buyItem('${item.id}', ${item.price})">${isOwned ? (isEq ? 'Снять' : 'Надеть') : `${item.price} 🪙`}</button></div>`; 
            });
        }
        function buyItem(id, price) { 
            if (state.inventory[id]) { 
                if (state.equipped.pet === id) state.equipped.pet = 'none';
                else state.equipped.pet = id;
            } else if (state.coins >= price) { 
                state.coins -= price; state.inventory[id] = true; state.equipped.pet = id; 
            } else { tg.showAlert("Мало монет!"); return; } 
            updateUI(); 
        }

        function renderDuo() {
            const solo = document.getElementById('duo-area-solo'); const active = document.getElementById('duo-area-active');
            if(!solo || !active) return;

            if (currentMode === 'solo') {
                solo.style.display = 'block'; active.style.display = 'none';
            } else {
                solo.style.display = 'none'; active.style.display = 'block';
                document.getElementById('duo-my-name').innerText = state.nickname;
                document.getElementById('duo-partner-name').innerText = document.getElementById('partner-name').innerText;
                
                const med = allMedals.find(m => m.id === state.selectedMedal);
                const dMed = document.getElementById('duo-my-medal');
                if (med) dMed.innerHTML = `<span class="medal-emoji">${med.emoji}</span>`;
                else dMed.innerHTML = '';

                const status = document.getElementById('family-status'); const btnCont = document.getElementById('pregnancy-btn-container');
                if (state.hasBaby) { status.innerText = "👶 У вас есть малыш!"; btnCont.innerHTML = ""; } 
                else if (state.isPregnant) { status.innerText = `🤰 Беременна!`; btnCont.innerHTML = ""; } 
                else if (state.gender === 'female') { status.innerText = "Готова к материнству"; if (state.streakDays >= 7 || state.isAdmin) btnCont.innerHTML = `<button class="card-price" onclick="startPregnancy()">Забеременеть</button>`; else btnCont.innerHTML = `<div style="font-size:12px;color:#aaa;">Нужна серия 7 дней</div>`; } 
                else { status.innerText = "Самец"; btnCont.innerHTML = ""; }
            }
        }
        function startPregnancy() { state.isPregnant = true; state.pregnancyEnd = Date.now() + (7 * 24 * 60 * 60 * 1000); updateUI(); }

        document.getElementById('panda-wrapper').addEventListener('pointerdown', (e) => {
            if (state.energy <= 0) return; state.energy -= 1; state.coins += state.tapPower;
            let earn = state.tapPower; if (currentMode === 'bros' || currentMode === 'sisters') earn = Math.floor(earn * 1.5); state.coins += (earn - state.tapPower);

            const p = document.getElementById('panda-wrapper'); p.classList.remove('hit'); void p.offsetWidth; p.classList.add('hit');
            const earL = document.getElementById('ear-left'); const earR = document.getElementById('ear-right'); earL.style.transform = 'translateY(3px)'; earR.style.transform = 'translateY(3px)';
            setTimeout(() => { earL.style.transform = 'translateY(0)'; earR.style.transform = 'translateY(0)'; }, 200);

            const eyeL = document.getElementById('eye-L'); const eyeR = document.getElementById('eye-R'); eyeL.classList.remove('slow-open'); eyeR.classList.remove('slow-open'); eyeL.classList.add('closed'); eyeR.classList.add('closed');
            if(eyeTimeout) clearTimeout(eyeTimeout);
            eyeTimeout = setTimeout(() => { eyeL.classList.add('slow-open'); eyeR.classList.add('slow-open'); eyeL.classList.remove('closed'); eyeR.classList.remove('closed'); setTimeout(() => { eyeL.classList.remove('slow-open'); eyeR.classList.remove('slow-open'); }, 2100); }, 300);

            const coin = document.createElement('div'); coin.className = 'particle-coin'; coin.innerText = `+${earn}`; coin.style.left = (e.clientX - 15) + 'px'; coin.style.top = (e.clientY - 20) + 'px'; document.body.appendChild(coin); setTimeout(() => coin.remove(), 900);
            
            if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify({ type: "tap", power: earn })); ws.send(JSON.stringify({ type: "update_stats", coins: state.coins, gems: state.gems })); }
            updateUI();
        });

        function switchTab(tabId, btn) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active')); document.getElementById('screen-' + tabId).classList.add('active'); document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active')); if (btn) btn.classList.add('active');
            if (tabId === 'farm') renderFarm(); if (tabId === 'friends') { fetchFriends(); fetchLeaderboard(); }
        }

        function switchFriendsTab(tab, btn) {
            document.querySelectorAll('.tabs-sub .tab-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active');
            if (tab === 'list') {
                document.getElementById('friends-list-container').style.display = 'block';
                document.getElementById('leaderboard-container').style.display = 'none';
                fetchFriends();
            } else {
                document.getElementById('friends-list-container').style.display = 'none';
                document.getElementById('leaderboard-container').style.display = 'block';
                fetchLeaderboard();
            }
        }

        function loadGame() {
            const saved = localStorage.getItem('pandaUltimate'); if (saved) { try { state = { ...state, ...JSON.parse(saved) }; } catch(e) {} }
            
            if (!state.unlockedMedals) state.unlockedMedals = [];
            if (!state.unlockedFrames) state.unlockedFrames = [];
            if (!state.unlockedAnims) state.unlockedAnims = [];
            if (!state.giftHistory) state.giftHistory = [];

            if (myId === ADMIN_ID) { state.isAdmin = true; state.verified = true; state.gems = 999999; state.coins = 99999999; state.streakDays = 730; state.inventory = { pet_dog: true, pet_cat: true, pet_fox: true, pet_dragon: true }; state.equipped = { pet: 'pet_dragon' }; state.selectedMedal = 'mythic'; state.selectedFrame = 'legend'; state.selectedNickAnim = 'rainbow'; }
            
            if (!state.gender) document.getElementById('setup-screen').style.display = 'flex'; 
            else { document.getElementById('setup-screen').style.display = 'none'; applyGenderVisuals(); checkStreak(); updateUI(); connectWebSocket(); fetchFriends(); fetchLeaderboard(); updateAvatarUI(); }
        }

        function applyGenderVisuals() {
            const features = document.getElementById('gender-features'); const bow = document.getElementById('gender-bow'); const mouth = document.getElementById('mouth-path');
            if (state.gender === 'female') { features.innerHTML = `<ellipse cx="45" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" /><ellipse cx="155" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" /><path d="M 60 75 Q 65 70 75 75" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round"/><path d="M 140 75 Q 135 70 125 75" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round"/>`; bow.style.display = 'block'; mouth.setAttribute('d', 'M 92 112 Q 100 120 108 112'); } 
            else { features.innerHTML = `<path d="M 50 65 Q 70 60 85 70" fill="none" stroke="#111" stroke-width="4" stroke-linecap="round"/><path d="M 150 65 Q 130 60 115 70" fill="none" stroke="#111" stroke-width="4" stroke-linecap="round"/>`; bow.style.display = 'none'; mouth.setAttribute('d', 'M 92 112 L 108 112'); }
        }

        function checkStreak() {
            const now = Date.now(); const oneDay = 24 * 60 * 60 * 1000;
            if (state.lastLogin === 0) { state.lastLogin = now; state.streakDays = 1; } else { const d = Math.floor((now - state.lastLogin) / oneDay); if (d >= 1) { state.streakDays += d; state.lastLogin = now; } }
            let scale = 0.6 + (state.streakDays * 0.01); 
            if (scale > 1.2) scale = 1.2; 
            document.getElementById('panda-wrapper').style.transform = `scale(${scale})`; 
            saveGame();
        }

        function selectGender(g) { state.gender = g; document.getElementById('setup-screen').style.display = 'none'; applyGenderVisuals(); checkStreak(); saveGame(); updateUI(); connectWebSocket(); fetchFriends(); fetchLeaderboard(); }

        function connectWebSocket() {
            ws = new WebSocket(`${WS_URL}/ws/${roomId}/${myId}`);
            ws.onopen = () => { 
                document.getElementById('conn-status').innerText = "🟢 Онлайн"; 
                ws.send(JSON.stringify({ type: "set_name", name: state.nickname })); 
                ws.send(JSON.stringify({ type: "set_gender", gender: state.gender })); 
                ws.send(JSON.stringify({ type: "update_stats", coins: state.coins, gems: state.gems })); 
                
                // Если мы зашли по приглашению друга
                if (inviterId) {
                    ws.send(JSON.stringify({ type: "add_friend", inviter_id: inviterId }));
                    inviterId = null; // Отправляем только один раз
                }
                
                document.getElementById('loading').style.display = 'none'; 
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'room_state') {
                    const friend = data.players.find(p => String(p.id) !== myId);
                    if (friend) { 
                        currentMode = 'duo'; 
                        document.getElementById('partner-name').innerText = friend.name; 
                        const bg = document.getElementById('bg-container'); 
                        if (state.gender === 'male' && friend.gender === 'male') bg.className = 'bg-container bg-bro'; 
                        else if (state.gender === 'female' && friend.gender === 'female') bg.className = 'bg-container bg-sisters'; 
                        else bg.className = 'bg-container bg-romantic'; 
                        renderDuo();
                    } else { 
                        currentMode = 'solo'; 
                        document.getElementById('bg-container').className = 'bg-container'; 
                        renderDuo();
                    }
                } else if (data.type === 'player_tapped') { 
                    state.coins += data.power; updateUI(); 
                } else if (data.type === 'gift_received') {
                    state.giftsReceived += 1;
                    state.giftHistory.unshift({ from: data.from_name, gift: data.gift, time: Date.now() });
                    tg.showAlert(`🎁 Тебе подарили ${data.gift} от ${data.from_name}!`);
                    updateUI();
                } else if (data.type === 'friend_added') {
                    tg.showAlert(`🤝 Вы теперь друзья с ${data.friend_name}!`);
                    fetchFriends();
                }
            };
            ws.onclose = () => { document.getElementById('conn-status').innerText = "🔴 Оффлайн"; setTimeout(connectWebSocket, 3000); };
        }
        
        async function fetchFriends() {
            try {
                const res = await fetch(`${API_URL}/api/friends/${myId}`); const data = await res.json(); state.friends = data; const list = document.getElementById('friends-list'); if(!list) return;
                if (state.friends.length === 0) { list.innerHTML = `<p style="text-align:center; color:#888;">Пока нет друзей.</p>`; return; }
                list.innerHTML = state.friends.map(f => `
                    <div class="friend-item" onclick="viewProfile('${f.id}', '${f.name}', ${f.coins}, ${f.gifts || 0}, '${f.frame}', '${f.medal}', '${f.nick_style}', '${f.avatar}', ${f.verified}, ${JSON.stringify(f.gift_history || [])})">
                        <div class="friend-avatar">${f.avatar ? `<img src="${f.avatar}">` : '🐼'}</div>
                        <div class="friend-name-box">
                            <div class="friend-name-row">
                                <span class="${f.nick_style}">${f.name}</span>
                                ${f.medal !== 'none' ? `<span class="medal-emoji small">${allMedals.find(m => m.id === f.medal)?.emoji}</span>` : ''}
                                ${f.verified ? '<span class="verified-badge">✔</span>' : ''}
                            </div>
                            <div class="friend-sub">
                                <span class="status-dot ${f.online ? 'status-online' : 'status-offline'}"></span> ${f.online ? 'В сети' : 'Не в сети'}
                            </div>
                        </div>
                        <div class="friend-coins">${f.coins.toLocaleString()} 🪙</div>
                    </div>
                `).join('');
            } catch(e) { document.getElementById('friends-list').innerHTML = `<p style="text-align:center; color:#888;">Сервер просыпается...</p>`; }
        }

        async function fetchLeaderboard() {
            try {
                const res = await fetch(`${API_URL}/api/leaderboard`); const data = await res.json(); const list = document.getElementById('leaderboard-list');
                list.innerHTML = data.map((p, i) => `
                    <div class="leaderboard-item" onclick="viewProfile('${p.id}', '${p.name}', ${p.coins}, ${p.gifts || 0}, '${p.frame}', '${p.medal}', '${p.nick_style}', '${p.avatar}', ${p.verified}, ${JSON.stringify(p.gift_history || [])})">
                        <span class="lb-rank">${i + 1}.</span>
                        <div class="lb-avatar">${p.avatar ? `<img src="${p.avatar}">` : '🐼'}</div>
                        <span class="lb-name ${p.nick_style}">${p.name} ${p.medal !== 'none' ? `<span class="medal-emoji small">${allMedals.find(m => m.id === p.medal)?.emoji}</span>` : ''} ${p.verified ? '<span class="verified-badge">✔</span>' : ''} ${p.online ? '<span class="status-dot status-online"></span>' : ''}</span>
                        <span class="lb-coins">${p.coins.toLocaleString()} 🪙</span>
                    </div>
                `).join('');
            } catch(e) { document.getElementById('leaderboard-list').innerHTML = `<p style="text-align:center; color:#888;">Сервер просыпается...</p>`; }
        }
        
        let currentViewPlayerId = null;
        function viewProfile(id, name, coins, gifts, frameId, medalId, nickStyle, avatarUrl, isVerified, giftHistory) {
            currentViewPlayerId = id;
            document.getElementById('vp-name').innerText = name;
            document.getElementById('vp-name').className = `profile-name ${nickStyle}`;
            document.getElementById('vp-coins').innerText = coins.toLocaleString(); 
            document.getElementById('vp-gifts').innerText = gifts || 0;
            
            const vpAv = document.getElementById('vp-avatar');
            if (avatarUrl) vpAv.innerHTML = `<img src="${avatarUrl}">`; else vpAv.innerText = '🐼';
            
            const frameData = allFrames.find(f => f.id === frameId);
            document.getElementById('vp-frame').className = `avatar-frame ${frameData ? frameData.cssClass : 'default'}`;
            
            const medData = allMedals.find(m => m.id === medalId);
            const vpMed = document.getElementById('vp-medal');
            if (medData) { vpMed.style.display = 'block'; vpMed.innerText = medData.emoji; }
            else vpMed.style.display = 'none';

            if (isVerified) {
                document.getElementById('vp-name').innerHTML += ' <span class="verified-badge" style="font-size:16px; width:20px; height:20px;">✔</span>';
            }

            // Отображение истории подарков
            const historyContainer = document.getElementById('vp-gift-history');
            if (historyContainer) {
                if (giftHistory && giftHistory.length > 0) {
                    historyContainer.innerHTML = giftHistory.map(g => `<div class="gift-history-item"><span class="gift-history-icon">${g.gift}</span> <span>от <b>${g.from}</b></span></div>`).join('');
                } else {
                    historyContainer.innerHTML = '<div style="color:#888; font-size:12px;">Подарков пока нет</div>';
                }
            }

            document.getElementById('view-profile-modal').classList.add('active');
        }

        window.openGiftModal = function() { document.getElementById('gift-modal').classList.add('active'); };
        window.closeModal = function(id) { document.getElementById(id).classList.remove('active'); };
        window.sendGift = function(giftEmoji, price) {
            if (state.gems < price) { tg.showAlert("Недостаточно гемов! 💎"); return; }
            state.gems -= price; 
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "send_gift", to: currentViewPlayerId, gift: giftEmoji, cost: price, from_name: state.nickname }));
            }
            tg.showAlert(`🎁 Ты подарил ${giftEmoji}!`);
            closeModal('gift-modal');
            updateUI();
        };

        function claimChest() { document.getElementById('chest-modal').classList.remove('active'); state.lastChest = Date.now(); state.coins += 1000; tg.showAlert("+1000 монет!"); updateUI(); }
        
        // ИСПРАВЛЕНИЕ ССЫЛКИ: Всегда генерируем ссылку со своим ID (myId), а не с roomId
        function inviteFriend() { 
            const link = `https://t.me/nash_sad_69_bot/play?startapp=${myId}`; 
            const text = `Присоединяйся ко мне в игре!`; 
            if (tg.openTelegramLink) tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`); 
            else navigator.clipboard.writeText(link).then(() => tg.showAlert("Скопировано!")); 
        }

        setInterval(() => {
            if (state.energy < state.maxEnergy) state.energy = Math.min(state.maxEnergy, state.energy + state.regen);
            if (document.getElementById('screen-farm').classList.contains('active')) { renderFarm(); }
            const now = Date.now(); let changed = false;
            state.bamboos.forEach(b => { if (b.stage === 1 && now - b.planted > 60000) { b.stage = 2; changed = true; } if (b.stage === 2 && now - b.planted > 120000) { b.stage = 3; changed = true; } });
            if (changed) saveGame(); 
            
            if(document.getElementById('coins')) document.getElementById('coins').innerText = Math.floor(state.coins).toLocaleString();
            if(document.getElementById('energy')) document.getElementById('energy').innerText = Math.floor(state.energy);
            if(document.getElementById('energy-fill')) document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';
        }, 1000);

        loadGame();
    </script>
</body>
</html>
"""

@app.get("/")
async def serve_game():
    return HTMLResponse(content=HTML_CONTENT)

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    if user_id not in players_db:
        players_db[user_id] = {"name": f"Panda_{user_id[:4]}", "coins": 0, "gems": 0, "gender": "male", "last_active": time.time(), "friends": [], "gifts": 0, "gift_history": [], "verified": True if user_id == '6877882967' else False, "avatar": "", "frame": "default", "medal": "none", "nick_style": "nick-default"}
    else:
        players_db[user_id]["last_active"] = time.time()
        
    if room_id not in rooms: rooms[room_id] = {"players": {}, "joint_progress": 0}
    
    for existing_uid in rooms[room_id]["players"].keys():
        if existing_uid != user_id:
            if existing_uid not in players_db[user_id]["friends"]: players_db[user_id]["friends"].append(existing_uid)
            if user_id not in players_db[existing_uid]["friends"]: players_db[existing_uid]["friends"].append(user_id)

    rooms[room_id]["players"][user_id] = websocket
    await broadcast_room_state(room_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                players_db[user_id]["last_active"] = time.time()
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue
                
            if message.get("type") == "set_name":
                new_name = message.get("name", "")
                if new_name and len(new_name) <= 15:
                    players_db[user_id]["name"] = new_name
                    await broadcast_room_state(room_id)
                continue

            if message.get("type") == "set_gender":
                players_db[user_id]["gender"] = message.get("gender", "male")
                await broadcast_room_state(room_id)
                continue
                
            if message.get("type") == "update_stats":
                players_db[user_id]["coins"] = message.get("coins", 0)
                players_db[user_id]["gems"] = message.get("gems", 0)
                players_db[user_id]["avatar"] = message.get("avatar", "")
                players_db[user_id]["frame"] = message.get("frame", "default")
                players_db[user_id]["medal"] = message.get("medal", "none")
                players_db[user_id]["nick_style"] = message.get("nick_style", "nick-default")
                players_db[user_id]["last_active"] = time.time()
                continue

            if message.get("type") == "add_friend":
                inviter_id = message.get("inviter_id")
                if inviter_id in players_db and inviter_id != user_id:
                    if inviter_id not in players_db[user_id]["friends"]: players_db[user_id]["friends"].append(inviter_id)
                    if user_id not in players_db[inviter_id]["friends"]: players_db[inviter_id]["friends"].append(user_id)
                    
                    # Уведомляем обоих
                    await websocket.send_text(json.dumps({"type": "friend_added", "friend_name": players_db[inviter_id]["name"]}))
                    if inviter_id in rooms.get(inviter_id, {}).get("players", {}):
                        try: await rooms[inviter_id]["players"][inviter_id].send_text(json.dumps({"type": "friend_added", "friend_name": players_db[user_id]["name"]}))
                        except: pass
                continue
                
            if message.get("type") == "send_gift":
                target_id = message.get("to")
                gift_type = message.get("gift")
                from_name = message.get("from_name", "Друг")
                
                if target_id in players_db:
                    players_db[target_id]["gifts"] += 1
                    players_db[target_id]["gift_history"].append({"from": from_name, "gift": gift_type, "time": time.time()})
                    
                    if target_id in rooms.get(room_id, {}).get("players", {}):
                        try: await rooms[room_id]["players"][target_id].send_text(json.dumps({"type": "gift_received", "gift": gift_type, "from_name": from_name}))
                        except: pass
                continue
                
            if message.get("type") == "tap":
                if len(rooms[room_id]["players"]) > 1:
                    rooms[room_id]["joint_progress"] += 0.5
                    if rooms[room_id]["joint_progress"] >= 100: rooms[room_id]["joint_progress"] = 0
                    await broadcast(room_id, {"type": "joint_progress", "progress": rooms[room_id]["joint_progress"]})

                await broadcast(room_id, {"type": "player_tapped", "user_id": user_id, "power": message.get("power", 1)}, exclude_user=user_id)
    except WebSocketDisconnect:
        if user_id in rooms[room_id]["players"]: del rooms[room_id]["players"][user_id]
        if len(rooms[room_id]["players"]) == 0: del rooms[room_id]
        else: await broadcast_room_state(room_id)

@app.get("/api/leaderboard")
async def get_leaderboard():
    sorted_players = sorted(players_db.items(), key=lambda x: x[1]["coins"], reverse=True)[:50]
    result = []
    for uid, data in sorted_players:
        is_online = (time.time() - data["last_active"]) < 120
        result.append({"id": uid, "name": data["name"], "coins": data["coins"], "online": is_online, "gifts": data.get("gifts", 0), "gift_history": data.get("gift_history", []), "verified": data.get("verified", False), "avatar": data.get("avatar", ""), "frame": data.get("frame", "default"), "medal": data.get("medal", "none"), "nick_style": data.get("nick_style", "nick-default")})
    return result

@app.get("/api/friends/{user_id}")
async def get_friends(user_id: str):
    if user_id not in players_db: return []
    friends_list = []
    for f_id in players_db[user_id]["friends"]:
        if f_id in players_db:
            f_data = players_db[f_id]
            is_online = (time.time() - f_data["last_active"]) < 120
            friends_list.append({"id": f_id, "name": f_data["name"], "coins": f_data["coins"], "online": is_online, "gifts": f_data.get("gifts", 0), "gift_history": f_data.get("gift_history", []), "verified": f_data.get("verified", False), "avatar": f_data.get("avatar", ""), "frame": f_data.get("frame", "default"), "medal": f_data.get("medal", "none"), "nick_style": f_data.get("nick_style", "nick-default")})
    return friends_list

async def broadcast_room_state(room_id: str):
    if room_id in rooms:
        players_list = []
        for uid in rooms[room_id]["players"].keys():
            if uid in players_db: players_list.append({"id": uid, "name": players_db[uid]["name"], "gender": players_db[uid]["gender"]})
            else: players_list.append({"id": uid, "name": f"Panda_{uid[:4]}", "gender": "male"})
        await broadcast(room_id, {"type": "room_state", "players": players_list})

async def broadcast(room_id: str, message: dict, exclude_user: str = None):
    if room_id in rooms:
        for uid, connection in list(rooms[room_id]["players"].items()):
            if uid != exclude_user:
                try: await connection.send_text(json.dumps(message))
                except: pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
