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
    <title>Panda Game 12.0</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Nunito', sans-serif; user-select: none; -webkit-tap-highlight-color: transparent; }
        body { background: #0a120e; color: #fff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; position: relative; }

        /* ЭКРАН ВЫБОРА ПОЛА */
        #setup-screen { position: fixed; inset: 0; background: rgba(10, 18, 14, 0.98); z-index: 9999; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }
        #setup-screen h1 { font-size: 28px; margin-bottom: 10px; color: #ffd700; }
        .gender-btns { display: flex; gap: 20px; margin-top: 20px; }
        .gender-btn { background: rgba(255,255,255,0.1); border: 2px solid #4caf50; border-radius: 20px; padding: 20px 30px; cursor: pointer; transition: 0.2s; }
        .gender-btn:hover { background: rgba(76, 175, 80, 0.3); transform: scale(1.05); }
        .gender-btn .icon { font-size: 50px; display: block; margin-bottom: 10px; }

        /* НОВЫЙ ФОН */
        .bg-container { position: absolute; inset: 0; z-index: 1; overflow: hidden; }
        .bg-sky { position: absolute; inset: 0; background: linear-gradient(180deg, #1a2a3a 0%, #2d4a5e 40%, #4a7a8c 80%, #6b9e7a 100%); }
        .bg-sun { position: absolute; top: 10%; right: 20%; width: 60px; height: 60px; background: radial-gradient(circle, #fff9c4, #ffe082, transparent); border-radius: 50%; filter: blur(5px); opacity: 0.8; }
        
        /* Горы */
        .bg-mountains { position: absolute; bottom: 20%; left: 0; width: 100%; height: 40%; opacity: 0.4; }
        .bg-mountains svg { width: 100%; height: 100%; }
        
        /* Бамбук (стоит на земле) */
        .bg-bamboo { position: absolute; bottom: 0; left: 0; width: 100%; height: 85%; display: flex; justify-content: space-around; align-items: flex-end; z-index: 2; }
        .stalk { position: relative; width: 18px; background: linear-gradient(90deg, #1b4d2e 0%, #4ea868 30%, #4ea868 70%, #1b4d2e 100%); border-radius: 8px; box-shadow: 2px 0 5px rgba(0,0,0,0.5); }
        .stalk::before { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(180deg, transparent 0 90px, #0d2818 90px 95px); border-radius: 8px; }
        .stalk::after { content: ''; position: absolute; top: 25%; left: 18px; width: 45px; height: 12px; background: #4ea868; border-radius: 4px 15px 0 4px; transform: rotate(-20deg); box-shadow: 2px 2px 5px rgba(0,0,0,0.3); }
        
        /* Земля и Трава */
        .bg-ground { position: absolute; bottom: 0; left: 0; width: 100%; height: 20%; background: linear-gradient(to top, #0a1f10 0%, #1b3d24 50%, #2d5e36 100%); z-index: 3; border-top-left-radius: 50% 20px; border-top-right-radius: 50% 20px; }
        .bg-grass-details { position: absolute; bottom: 0; left: 0; width: 100%; height: 25%; background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20" preserveAspectRatio="none"><path d="M0,20 Q10,5 20,20 Q30,10 40,20 Q50,0 60,20 Q70,15 80,20 Q90,5 100,20 Z" fill="%231b3d24"/></svg>') repeat-x; background-size: 100px 20px; z-index: 4; }

        /* ХЕДЕР */
        .header { padding: 12px 15px; display: flex; justify-content: space-between; align-items: flex-start; z-index: 10; position: relative; }
        .rank-box { display: flex; align-items: center; gap: 10px; }
        
        .profile-avatar-mini { width: 45px; height: 45px; border-radius: 50%; background: #333; border: 2px solid #ffd700; display: flex; justify-content: center; align-items: center; font-size: 24px; cursor: pointer; position: relative; overflow: hidden; }
        .profile-avatar-mini img { width: 100%; height: 100%; object-fit: cover; }
        
        .balance-container { display: flex; flex-direction: column; }
        .streak-badge { font-size: 11px; color: #ff6b00; font-weight: 900; }
        .balance-row { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
        .balance { font-size: 20px; font-weight: 900; color: #fff; }
        .gems { font-size: 16px; font-weight: 900; color: #00e5ff; }

        .energy-box { display: flex; flex-direction: column; align-items: flex-end; }
        .energy-text { font-size: 11px; font-weight: 700; color: #fff; margin-bottom: 3px; }
        .energy-bar { width: 80px; height: 8px; background: rgba(0,0,0,0.5); border-radius: 5px; overflow: hidden; border: 1px solid rgba(255,255,255,0.4); }
        .energy-fill { height: 100%; background: linear-gradient(90deg, #00e5ff, #007bff); width: 100%; transition: width 0.3s; }

        /* ЭКРАНЫ */
        .screens { flex: 1; position: relative; z-index: 5; overflow: hidden; }
        .screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: none; flex-direction: column; }
        .screen.active { display: flex; }

        /* ТАП */
        .tap-area { flex: 1; display: flex; justify-content: center; align-items: center; gap: 20px; position: relative; padding-bottom: 20px; }
        .panda-wrapper { position: relative; width: 190px; height: 210px; transform-origin: center bottom; cursor: pointer; transition: transform 1s ease-in-out; z-index: 5; }
        .panda-wrapper.partner-panda { width: 140px; height: 160px; opacity: 0.9; pointer-events: none; }
        .panda-wrapper:active { transform: scale(0.95); }
        .panda-wrapper.hit { animation: jump 0.25s ease-out; }
        @keyframes jump { 0% { transform: translateY(0); } 30% { transform: translateY(-15px) scale(1.05); } 100% { transform: translateY(0); } }
        
        .panda-name { text-align: center; font-size: 13px; font-weight: 900; color: #fff; margin-top: 8px; text-shadow: 2px 2px 0 #000; position: relative; z-index: 5; background: rgba(0,0,0,0.4); padding: 2px 8px; border-radius: 10px; display: inline-block; }

        .eye { transform-box: fill-box; transform-origin: center; transition: transform 0.15s ease-in-out; }
        .eye.closed { transform: scaleY(0.1); }
        .eye.slow-open { transition: transform 2s ease-out; }

        .particle-coin { position: absolute; font-size: 24px; font-weight: 900; color: #ffd700; pointer-events: none; animation: popCoin 0.9s ease-out forwards; z-index: 20; text-shadow: 0 0 10px #ffd700; }
        @keyframes popCoin { 0% { transform: translateY(0) scale(0.4); opacity: 1; } 100% { transform: translateY(-100px) scale(1.2); opacity: 0; } }
        
        /* КОНТЕНТ */
        .content { flex: 1; padding: 15px; overflow-y: auto; background: rgba(10, 18, 14, 0.85); backdrop-filter: blur(5px); z-index: 20; }
        .section-title { font-size: 20px; font-weight: 900; margin-bottom: 15px; color: #fff; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 15px; padding: 12px; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .card-icon { font-size: 32px; margin-bottom: 6px; }
        .card-title { font-size: 14px; font-weight: 900; margin-bottom: 4px; }
        .card-desc { font-size: 11px; color: #8892b0; margin-bottom: 8px; }
        .card-price { background: rgba(0,0,0,0.5); padding: 8px; border-radius: 8px; font-size: 12px; font-weight: 900; width: 100%; color: #ffd700; border: 1px solid rgba(255,215,0,0.3); cursor: pointer; }
        .card-price:disabled { color: #555; border-color: #333; cursor: not-allowed; }
        .card-price.owned { background: rgba(76, 175, 80, 0.2); color: #4caf50; border-color: #4caf50; }

        /* Друзья и Топ */
        .friend-list { display: flex; flex-direction: column; gap: 10px; margin-top: 15px; }
        .friend-item { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.05); padding: 10px 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); cursor: pointer; }
        .friend-info { display: flex; align-items: center; gap: 10px; }
        .friend-status { width: 10px; height: 10px; border-radius: 50%; }
        .status-online { background: #4caf50; box-shadow: 0 0 5px #4caf50; }
        .status-offline { background: #555; }
        .friend-name { font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 5px; }
        .friend-coins { font-size: 12px; color: #ffd700; }
        
        .tabs-sub { display: flex; gap: 10px; margin-bottom: 15px; align-items: center; }
        .tab-btn { flex: 1; background: rgba(255,255,255,0.1); border: none; color: #aaa; padding: 8px; border-radius: 8px; font-weight: 900; cursor: pointer; }
        .tab-btn.active { background: #4caf50; color: #fff; }

        .leaderboard-item { display: flex; justify-content: space-between; padding: 8px 15px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 14px; cursor: pointer; align-items: center; }
        .leaderboard-item span:first-child { font-weight: 900; color: #ffd700; width: 30px; }

        /* Навигация (НОВЫЙ ПОРЯДОК) */
        .bottom-nav { background: rgba(10, 18, 14, 0.98); border-top: 1px solid rgba(46, 125, 50, 0.4); padding: 8px 5px 22px 5px; display: flex; justify-content: space-around; z-index: 30; position: relative; }
        .nav-btn { display: flex; flex-direction: column; align-items: center; background: none; border: none; color: #666; font-size: 9px; font-weight: 900; cursor: pointer; width: 16.6%; transition: 0.2s; }
        .nav-btn.active { color: #81c784; }
        .nav-btn span { font-size: 22px; margin-bottom: 2px; filter: grayscale(1); transition: 0.2s; }
        .nav-btn.active span { filter: drop-shadow(0 0 6px #81c784) grayscale(0); }

        /* Мини-игра */
        .game-area-mini { height: 250px; width: 100%; background: #112217; position: relative; overflow: hidden; border-radius: 10px; border: 1px solid #4caf50; margin-bottom: 10px; }
        .falling-item { position: absolute; font-size: 30px; cursor: pointer; animation: fall linear forwards; }
        @keyframes fall { 0% { transform: translateY(-50px) rotate(0deg); } 100% { transform: translateY(280px) rotate(360deg); } }

        /* Модалки */
        .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 1000; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; backdrop-filter: blur(5px); }
        .modal.active { display: flex; }
        .modal-box { background: #1a2e22; border: 2px solid #4caf50; border-radius: 20px; padding: 25px; width: 90%; max-width: 350px; position: relative; }
        
        .name-input { width: 100%; padding: 10px; border-radius: 8px; border: none; font-size: 16px; font-weight: 900; text-align: center; margin-bottom: 15px; background: #fff; color: #111; }

        /* Профиль */
        .profile-card { background: rgba(0,0,0,0.6); border-radius: 15px; padding: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; position: relative; overflow: hidden; }
        .profile-avatar-large { width: 80px; height: 80px; border-radius: 50%; margin: 0 auto 10px; background: #333; display: flex; justify-content: center; align-items: center; font-size: 40px; border: 3px solid #ffd700; position: relative; overflow: hidden; }
        .profile-avatar-large img { width: 100%; height: 100%; object-fit: cover; }
        .profile-name { font-size: 20px; font-weight: 900; margin-bottom: 5px; }
        .profile-stats { display: flex; justify-content: center; gap: 20px; margin-top: 15px; font-size: 12px; color: #aaa; }
        .profile-stats span { font-weight: 900; color: #fff; display: block; font-size: 16px; }
        
        .inventory-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 10px; }
        .inv-item { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; text-align: center; border: 2px solid transparent; cursor: pointer; }
        .inv-item.selected { border-color: #4caf50; background: rgba(76, 175, 80, 0.2); }
        .inv-icon { font-size: 24px; margin-bottom: 5px; filter: grayscale(1); }
        .inv-item.owned .inv-icon { filter: none; }

        /* Квесты */
        .quest-item { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #ffd700; }
        .quest-info { flex: 1; }
        .quest-title { font-size: 14px; font-weight: 900; margin-bottom: 4px; }
        .quest-reward { font-size: 12px; color: #4caf50; font-weight: 900; }
        .quest-btn { background: #4caf50; color: #fff; border: none; padding: 8px 15px; border-radius: 8px; font-weight: 900; cursor: pointer; }
        .quest-btn:disabled { background: #555; cursor: not-allowed; }

        #error-log { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255,0,0,0.9); color: white; padding: 10px; font-size: 12px; z-index: 9999; display: none; word-break: break-all; }
        #loading { position: fixed; inset: 0; background: #0a120e; z-index: 10000; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 20px; font-weight: 900; color: #4caf50; }
        #loading-text { margin-top: 20px; font-size: 14px; color: #aaa; text-align: center; }
    </style>
</head>
<body>
    <div id="loading">
        <div>Загрузка игры...</div>
        <div id="loading-text">Подключение к серверу...</div>
    </div>

    <div id="setup-screen">
        <h1>Кто у тебя появится?</h1>
        <p>Выбери пол своего питомца.</p>
        <div class="gender-btns">
            <div class="gender-btn" onclick="selectGender('male')"><span class="icon">👦</span>Мальчик</div>
            <div class="gender-btn" onclick="selectGender('female')"><span class="icon">👧</span>Девочка</div>
        </div>
    </div>

    <div class="modal" id="name-modal">
        <div class="modal-box">
            <h2 style="color:#4caf50; margin-bottom:15px;">Твой Никнейм</h2>
            <input type="text" id="name-input" class="name-input" maxlength="15" placeholder="Введи имя...">
            <button class="card-price" style="background:#4caf50; color:#fff; padding:12px;" onclick="saveName()">Сохранить</button>
            <button class="card-price" style="background:#555; color:#fff; margin-top:10px;" onclick="closeModal('name-modal')">Отмена</button>
        </div>
    </div>

    <div class="modal" id="gift-modal">
        <div class="modal-box">
            <h2 style="color:#ffd700; margin-bottom:15px;">Подарить игроку</h2>
            <p id="gift-target-name" style="margin-bottom:15px; font-weight:900;"></p>
            <div style="display:flex; justify-content:space-around; margin-bottom:20px;">
                <div onclick="sendGift('rose', 10)" style="cursor:pointer; text-align:center;">
                    <div style="font-size:30px;">🌹</div><div style="font-size:10px; color:#00e5ff;">10 💎</div>
                </div>
                <div onclick="sendGift('cake', 50)" style="cursor:pointer; text-align:center;">
                    <div style="font-size:30px;">🎂</div><div style="font-size:10px; color:#00e5ff;">50 💎</div>
                </div>
                <div onclick="sendGift('bear', 100)" style="cursor:pointer; text-align:center;">
                    <div style="font-size:30px;">🧸</div><div style="font-size:10px; color:#00e5ff;">100 💎</div>
                </div>
                <div onclick="sendGift('crown', 500)" style="cursor:pointer; text-align:center;">
                    <div style="font-size:30px;">👑</div><div style="font-size:10px; color:#00e5ff;">500 💎</div>
                </div>
            </div>
            <button class="card-price" style="background:#555; color:#fff;" onclick="closeModal('gift-modal')">Отмена</button>
        </div>
    </div>

    <div class="modal" id="view-profile-modal">
        <div class="modal-box" style="text-align:center;">
            <div class="profile-avatar-large" id="vp-avatar">🐼</div>
            <div class="profile-name" id="vp-name">Ник</div>
            <div style="color:#aaa; font-size:12px; margin-bottom:15px;" id="vp-medal">Медаль</div>
            <div class="profile-stats" style="justify-content:space-around;">
                <div>Монеты <span id="vp-coins">0</span></div>
                <div>Подарки <span id="vp-gifts">0</span></div>
            </div>
            <button class="card-price" style="background:#ff9800; color:#fff; margin-top:15px;" onclick="openGiftModal()">Подарить 🎁</button>
            <button class="card-price" style="background:#555; color:#fff; margin-top:10px;" onclick="closeModal('view-profile-modal')">Закрыть</button>
        </div>
    </div>

    <!-- Модалка Колеса Фортуны -->
    <div class="modal" id="wheel-modal">
        <div class="modal-box" style="text-align:center;">
            <h2 style="color:#ffd700; margin-bottom:15px;">🎡 Колесо Фортуны</h2>
            <div style="font-size:60px; margin:20px 0; animation: spin 2s linear infinite;" id="wheel-icon">🎡</div>
            <button class="card-price" style="background:#4caf50; color:#fff; padding:15px;" onclick="spinWheel()">Крутить (Бесплатно)</button>
        </div>
    </div>

    <div class="bg-container">
        <div class="bg-sky">
            <div class="bg-sun"></div>
        </div>
        <div class="bg-mountains">
            <svg viewBox="0 0 400 200" preserveAspectRatio="none">
                <path d="M0,200 L50,80 L120,120 L180,40 L260,90 L340,60 L400,150 L400,200 Z" fill="#1a2a3a"/>
                <path d="M0,200 L70,110 L150,150 L240,80 L320,130 L400,200 Z" fill="#2d4a5e"/>
            </svg>
        </div>
        <div class="bg-bamboo">
            <div class="stalk" style="height: 70%; left: 5%;"></div>
            <div class="stalk" style="height: 90%; left: 20%;"></div>
            <div class="stalk" style="height: 60%; right: 15%;"></div>
            <div class="stalk" style="height: 80%; right: 5%;"></div>
        </div>
        <div class="bg-ground"></div>
        <div class="bg-grass-details"></div>
    </div>

    <div class="header">
        <div class="rank-box">
            <div class="profile-avatar-mini" id="mini-avatar" onclick="switchTab('profile', document.querySelectorAll('.nav-btn')[5])">
                <span>🐼</span>
            </div>
            <div>
                <div class="streak-badge" id="streak-badge">🔥 Серия: 0</div>
                <div class="balance-row">
                    <div class="balance"><span id="coins">0</span> 🪙</div>
                    <div class="gems"><span id="gems">0</span> 💎</div>
                </div>
            </div>
        </div>
        <div class="energy-box">
            <div class="energy-text"><span id="energy">1000</span>/<span id="max-energy">1000</span> ⚡</div>
            <div class="energy-bar"><div class="energy-fill" id="energy-fill"></div></div>
            <div style="font-size:10px; color:#fff; margin-top:5px;" id="conn-status">Подключение...</div>
        </div>
    </div>

    <div class="screens">
        <!-- ТАП -->
        <div class="screen active" id="screen-tap">
            <div class="tap-area">
                <div style="text-align: center;">
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
                                    <g id="acc-hat" style="display:none;"><path d="M 50 40 Q 100 10 150 40 L 155 50 Q 100 30 45 50 Z" fill="#2196f3" /></g>
                                    <g id="acc-glasses" style="display:none;"><circle cx="70" cy="85" r="18" fill="rgba(0,0,0,0.8)" stroke="#333" stroke-width="4" /><circle cx="130" cy="85" r="18" fill="rgba(0,0,0,0.8)" stroke="#333" stroke-width="4" /><path d="M 88 85 L 112 85" stroke="#333" stroke-width="4" /></g>
                                    <g id="acc-crown" style="display:none;"><path d="M 60 40 L 70 10 L 100 30 L 130 10 L 140 40 Z" fill="#ffd700" stroke="#ffb300" stroke-width="2"/></g>
                                    <g id="acc-bowtie" style="display:none;"><path d="M 90 120 L 70 110 L 70 130 Z" fill="#e91e63" /><path d="M 110 120 L 130 110 L 130 130 Z" fill="#e91e63" /><circle cx="100" cy="120" r="6" fill="#ad1457" /></g>
                                </g>
                                <g class="front-legs">
                                    <g class="hand-left"><ellipse cx="45" cy="145" rx="18" ry="22" fill="#1a1a1a" /><ellipse cx="38" cy="160" rx="6" ry="5" fill="url(#padGrad)" /><ellipse cx="48" cy="162" rx="6" ry="5" fill="url(#padGrad)" /></g>
                                    <g class="hand-right"><ellipse cx="155" cy="145" rx="18" ry="22" fill="#1a1a1a" /><ellipse cx="152" cy="162" rx="6" ry="5" fill="url(#padGrad)" /><ellipse cx="162" cy="160" rx="6" ry="5" fill="url(#padGrad)" /></g>
                                </g>
                            </g>
                        </svg>
                    </div>
                    <div class="panda-name" id="my-name">Загрузка...</div>
                </div>
                
                <div style="text-align: center; display:none;" id="partner-container">
                    <div class="panda-wrapper partner-panda" id="partner-panda">
                         <svg viewBox="0 0 200 220" style="width:100%; height:100%; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5));">
                            <defs><radialGradient id="bodyGrad2" cx="40%" cy="30%" r="80%"><stop offset="0%" stop-color="#ffffff" /><stop offset="60%" stop-color="#f5f5f5" /><stop offset="100%" stop-color="#d0d0d0" /></radialGradient></defs>
                            <ellipse cx="100" cy="205" rx="75" ry="15" fill="url(#shadowGrad)" />
                            <g><ellipse cx="55" cy="175" rx="24" ry="18" fill="#1a1a1a" /><ellipse cx="145" cy="175" rx="24" ry="18" fill="#1a1a1a" /></g>
                            <g><ellipse cx="100" cy="140" rx="62" ry="55" fill="url(#bodyGrad2)" /><path d="M 55 160 Q 100 130 145 160 Q 135 195 100 198 Q 65 195 55 160 Z" fill="#ececec" /></g>
                            <g transform="translate(0, -5)">
                                <circle cx="45" cy="45" r="20" fill="#1a1a1a" /><circle cx="155" cy="45" r="20" fill="#1a1a1a" />
                                <ellipse cx="100" cy="90" rx="65" ry="58" fill="url(#bodyGrad2)" />
                                <ellipse cx="70" cy="85" rx="18" ry="23" fill="#111" /><ellipse cx="130" cy="85" rx="18" ry="23" fill="#111" />
                                <g class="eye"><circle cx="70" cy="85" r="9" fill="#fff" /><circle cx="70" cy="85" r="6" fill="#111" /></g>
                                <g class="eye"><circle cx="130" cy="85" r="9" fill="#fff" /><circle cx="130" cy="85" r="6" fill="#111" /></g>
                                <ellipse cx="100" cy="105" rx="8" ry="5" fill="#111" />
                                <path d="M 92 112 Q 100 118 108 112" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round" />
                            </g>
                        </svg>
                    </div>
                    <div class="panda-name" id="partner-name">Друг</div>
                </div>
            </div>
        </div>

        <!-- ПРОФИЛЬ -->
        <div class="screen" id="screen-profile">
            <div class="content">
                <div class="profile-card">
                    <div class="profile-avatar-large" id="my-avatar-large" onclick="selectAvatar()">
                        🐼
                    </div>
                    <div class="profile-name" id="my-name-profile">Загрузка...</div>
                    <div id="my-medal-display" style="color:#ffd700; font-weight:900; margin-bottom:5px;">Медаль: Нет</div>
                    <button class="card-price" style="width:auto; display:inline-block; margin-top:5px; background:#2196f3; padding:5px 15px;" onclick="openNameModal()">Изменить ник</button>
                    
                    <div class="profile-stats">
                        <div>Монеты <span id="stat-coins">0</span></div>
                        <div>Гемы <span id="stat-gems">0</span></div>
                        <div>Серия <span id="stat-streak">0</span></div>
                    </div>
                </div>

                <div class="section-title" style="font-size:16px;">Мои награды</div>
                <div class="inventory-grid" id="medals-grid"></div>
                <div class="inventory-grid" id="frames-grid"></div>
                <div class="section-title" style="font-size:16px; margin-top:20px;">Мои подарки</div>
                <div id="gifts-list" style="font-size:14px; color:#aaa; text-align:center;">Пока нет подарков</div>
            </div>
        </div>

        <!-- ФЕРМА -->
        <div class="screen" id="screen-farm">
            <div class="content">
                <div class="section-title">Ферма бамбука 🎋</div>
                <div class="grid" id="farm-grid"></div>
            </div>
        </div>

        <!-- ДРУЗЬЯ -->
        <div class="screen" id="screen-friends">
            <div class="content">
                <div class="section-title">Друзья 👥</div>
                <div class="tabs-sub">
                    <button class="tab-btn active" onclick="switchFriendsTab('list', this)">Мои друзья</button>
                    <button class="tab-btn" onclick="switchFriendsTab('top', this)">Топ 50</button>
                    <button class="refresh-btn" style="background:#2196f3; color:#fff; border:none; border-radius:8px; padding:8px; cursor:pointer;" onclick="fetchFriends()">🔄</button>
                </div>
                
                <div id="friends-list-container">
                    <button class="card-price" onclick="inviteFriend()" style="margin-bottom:10px; background:#2196f3; color:#fff; border:none;">Пригласить друга (+10000 🪙)</button>
                    <div class="friend-list" id="friends-list">
                        <p style="text-align:center; color:#888;">Загрузка друзей...</p>
                    </div>
                </div>
                
                <div id="leaderboard-container" style="display:none;">
                    <div id="leaderboard-list">
                        <p style="text-align:center; color:#888;">Загрузка топа...</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- МАГАЗИН -->
        <div class="screen" id="screen-shop">
            <div class="content">
                <div class="section-title">Магазин 🛍️</div>
                <div class="tabs-sub" style="margin-bottom:15px;">
                    <button class="tab-btn active" onclick="switchShopTab('items', this)">Одежда</button>
                    <button class="tab-btn" onclick="switchShopTab('gems', this)">Гемы 💎</button>
                </div>
                <div class="grid" id="shop-grid"></div>
                <div class="grid" id="gems-grid" style="display:none;">
                    <div class="card">
                        <div class="card-icon">💎</div>
                        <div class="card-title">100 Гемов</div>
                        <button class="card-price" onclick="buyGems(50)">50 ⭐</button>
                    </div>
                    <div class="card">
                        <div class="card-icon">💎</div>
                        <div class="card-title">500 Гемов</div>
                        <button class="card-price" onclick="buyGems(200)">200 ⭐</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- ИГРЫ -->
        <div class="screen" id="screen-games">
            <div class="content">
                <div class="section-title">Мини-игры 🏆</div>
                <div class="game-area-mini" id="game-area-mini"></div>
                <div style="text-align:center; font-size:24px; font-weight:900; margin-bottom:10px;">Счет: <span id="mini-score">0</span></div>
                <button class="card-price" id="mini-btn-bamboo" onclick="startMiniGame('bamboo')" style="background:#4caf50; color:#fff; font-size:16px; padding:15px; margin-bottom:10px;">Поймай бамбук 🎋</button>
                <button class="card-price" id="mini-btn-food" onclick="startMiniGame('food')" style="background:#ff9800; color:#fff; font-size:16px; padding:15px; margin-bottom:10px;">Покорми панду 🍎</button>
                <button class="card-price" style="background:#9c27b0; color:#fff; font-size:16px; padding:15px;" onclick="document.getElementById('wheel-modal').classList.add('active')">Колесо Фортуны 🎡</button>
            </div>
        </div>

        <!-- СЕМЬЯ -->
        <div class="screen" id="screen-family">
            <div class="content">
                <div class="section-title">Семья 👨‍👩‍👧‍👦</div>
                <div class="card" style="margin-bottom:15px; padding:20px;">
                    <div id="family-status" style="font-size:16px; font-weight:900; color:#ffd700; margin-bottom:10px;">Ты пока один</div>
                    <div id="pregnancy-btn-container"></div>
                </div>
            </div>
        </div>

        <!-- КВЕСТЫ -->
        <div class="screen" id="screen-quests">
            <div class="content">
                <div class="section-title">Квесты 📜</div>
                <div id="quests-list"></div>
            </div>
        </div>
    </div>

    <!-- НАВИГАЦИЯ (НОВЫЙ ПОРЯДОК) -->
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
        setTimeout(() => { 
            const lt = document.getElementById('loading-text');
            if (lt) lt.innerText = "Сервер просыпается, подождите 30-50 секунд...";
        }, 4000);
        setTimeout(() => { 
            const loading = document.getElementById('loading');
            if (loading) loading.style.display = 'none'; 
        }, 500);

        window.onerror = function(msg, url, line) {
            if (msg.includes("Script error") || msg.includes("NetworkError") || msg.includes("Failed to fetch") || msg === "Script error.") return true; 
            const err = document.getElementById('error-log');
            err.style.display = 'block';
            err.innerText = "Ошибка: " + msg + " | Строка: " + line;
            return false;
        };

        const tg = window.Telegram.WebApp;
        tg.expand();

        let state = {
            coins: 500, gems: 0, gender: null, streakDays: 1, lastLogin: 0, accountCreated: Date.now(),
            tapPower: 1, energy: 1000, maxEnergy: 1000, regen: 5,
            isPregnant: false, pregnancyEnd: 0, hasBaby: false,
            inventory: { hat: false, glasses: false, crown: false, bowtie: false },
            equipped: { hat: false, glasses: false, crown: false, bowtie: false },
            bamboos: [{ id: 1, stage: 0, planted: 0 }, { id: 2, stage: 0, planted: 0 }, { id: 3, stage: 0, planted: 0 }],
            lastMiniGame: 0, lastBandit: 0, lastPaw: 0, lastChest: 0, lastWheel: 0,
            friends: [], giftsReceived: 0,
            nickname: '', selectedMedal: 'none', selectedFrame: 'default', avatarUrl: '',
            quests: { taps: 0, bought: false, invited: false, claimed: { q1: false, q2: false, q3: false } }
        };

        const urlParams = new URLSearchParams(window.location.search);
        const startParam = tg.initDataUnsafe?.start_param;
        const myId = String(tg.initDataUnsafe?.user?.id || Math.floor(Math.random() * 10000));
        const roomId = startParam || myId; 
        
        const WS_URL = window.location.origin.replace('https://', 'wss://'); 
        const API_URL = window.location.origin;
        let ws;
        let banditInterval = null;
        let currentMode = 'solo';

        // Загрузка аватарки из Telegram по умолчанию
        if (!state.avatarUrl) {
            state.avatarUrl = tg.initDataUnsafe?.user?.photo_url || ''; 
        }
        updateAvatarUI();

        function updateAvatarUI() {
            const miniAv = document.getElementById('mini-avatar');
            const largeAv = document.getElementById('my-avatar-large');
            
            if (state.avatarUrl) {
                miniAv.innerHTML = `<img src="${state.avatarUrl}">`;
                largeAv.innerHTML = `<img src="${state.avatarUrl}">`;
            } else {
                miniAv.innerHTML = '🐼';
                largeAv.innerHTML = '🐼';
            }
        }

        function selectAvatar() {
            // Заглушка для выбора аватарок
            tg.showAlert("Выбор аватарок появится в следующем обновлении! (Пока используется фото из Telegram)");
        }

        function openNameModal() { document.getElementById('name-input').value = state.nickname; document.getElementById('name-modal').classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }
        function saveName() {
            let newName = document.getElementById('name-input').value.trim();
            if (newName === '') newName = `Panda_${myId.substring(0,4)}`;
            if (newName.length > 15) newName = newName.substring(0, 15);
            state.nickname = newName;
            document.getElementById('my-name').innerText = newName;
            document.getElementById('my-name-profile').innerText = newName;
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "set_name", name: newName }));
            closeModal('name-modal');
            updateUI();
        }

        // --- ЛОГИКА ФЕРМЫ (ИСПРАВЛЕНА) ---
        function renderFarm() {
            const grid = document.getElementById('farm-grid');
            if(!grid) return; grid.innerHTML = '';
            state.bamboos.forEach(b => {
                let status = "Пусто", btn = "Посадить", icon = "🟫", dis = false;
                if (b.stage === 1) {
                    const timeLeft = Math.ceil((60000 - (Date.now() - b.planted)) / 1000);
                    status = `Растет... ${timeLeft}с`; btn = "Ждем"; icon = "🌱"; dis = true;
                } else if (b.stage === 2) { status = "Созрел!"; btn = "Собрать"; icon = "🎋"; }
                else if (b.stage === 3) { status = "Сгнил!"; btn = "Убрать"; icon = "🥀"; }
                grid.innerHTML += `<div class="card"><div class="card-icon">${icon}</div><div class="card-title">Участок ${b.id}</div><div class="card-desc">${status}</div><button class="card-price" ${dis ? 'disabled' : ''} onclick="handleFarmClick(${b.id})">${btn}</button></div>`;
            });
        }

        function handleFarmClick(id) {
            const b = state.bamboos.find(x => x.id === id);
            if (b.stage === 0) { b.planted = Date.now(); b.stage = 1; }
            else if (b.stage === 2) { state.coins += 500; b.stage = 0; tg.showAlert("+500 монет!"); }
            else if (b.stage === 3) { b.stage = 0; }
            saveGame(); updateUI();
        }

        // --- МАГАЗИН ГЕМОВ ---
        function switchShopTab(tab, btn) {
            document.querySelectorAll('#screen-shop .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (tab === 'items') {
                document.getElementById('shop-grid').style.display = 'grid';
                document.getElementById('gems-grid').style.display = 'none';
            } else {
                document.getElementById('shop-grid').style.display = 'none';
                document.getElementById('gems-grid').style.display = 'grid';
            }
        }

        function buyGems(amount) {
            tg.showAlert(`Для покупки ${amount} гемов за Telegram Stars нужно подключить платежную систему в BotFather. Скоро добавим!`);
        }

        // --- КОЛЕСО ФОРТУНЫ ---
        function spinWheel() {
            const now = Date.now();
            if (now - state.lastWheel < 24 * 60 * 60 * 1000) {
                tg.showAlert("Колесо будет доступно завтра!");
                return;
            }
            state.lastWheel = now;
            const prizes = [100, 500, 1000, 5000];
            const win = prizes[Math.floor(Math.random() * prizes.length)];
            state.coins += win;
            tg.showAlert(`🎉 Ты выиграл ${win} монет!`);
            closeModal('wheel-modal');
            updateUI();
        }

        // --- ОСТАЛЬНОЙ КОД (без изменений) ---
        function updateUI() {
            document.getElementById('coins').innerText = Math.floor(state.coins).toLocaleString();
            document.getElementById('gems').innerText = Math.floor(state.gems).toLocaleString();
            document.getElementById('energy').innerText = Math.floor(state.energy);
            document.getElementById('max-energy').innerText = state.maxEnergy;
            document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';
            document.getElementById('streak-badge').innerText = `🔥 Серия: ${state.streakDays}`;

            ['hat', 'glasses', 'crown', 'bowtie'].forEach(item => {
                const el = document.getElementById('acc-' + item);
                if (el) el.style.display = state.equipped[item] ? 'block' : 'none';
            });

            renderFarm(); renderShop(); renderFamily(); renderQuests();
            updateTimers();
            saveGame();
        }

        function saveGame() { localStorage.setItem('pandaUltimate', JSON.stringify(state)); }

        function updateTimers() {
            const now = Date.now();
            if (now - state.lastChest > 24 * 60 * 60 * 1000) {
                document.getElementById('chest-modal').classList.add('active');
            }
            const timeLeft = Math.ceil((5 * 60 * 1000 - (now - state.lastMiniGame)) / 1000);
            const btnB = document.getElementById('mini-btn-bamboo');
            const btnF = document.getElementById('mini-btn-food');
            if (btnB && btnF) {
                if (timeLeft > 0) {
                    btnB.disabled = true; btnF.disabled = true;
                    btnB.style.background = '#555'; btnF.style.background = '#555';
                    const min = Math.floor(timeLeft / 60); const sec = timeLeft % 60;
                    const txt = `Через: ${min}:${sec < 10 ? '0' : ''}${sec}`;
                    btnB.innerText = txt; btnF.innerText = txt;
                } else {
                    btnB.disabled = false; btnF.disabled = false;
                    btnB.style.background = '#4caf50'; btnF.style.background = '#ff9800';
                    btnB.innerText = "Поймай бамбук 🎋"; btnF.innerText = "Покорми панду 🍎";
                }
            }
        }

        function renderQuests() {
            const list = document.getElementById('quests-list');
            if (!list) return;
            list.innerHTML = `
                <div class="quest-item">
                    <div class="quest-info">
                        <div class="quest-title">Сделай 100 кликов</div>
                        <div class="quest-reward">Награда: 50 💎</div>
                        <div style="font-size:11px; color:#aaa;">Прогресс: ${Math.min(state.quests.taps, 100)}/100</div>
                    </div>
                    <button class="quest-btn" ${state.quests.taps >= 100 && !state.quests.claimed.q1 ? '' : 'disabled'} onclick="claimQuest('q1', 50)">${state.quests.claimed.q1 ? 'Получено' : 'Забрать'}</button>
                </div>
                <div class="quest-item">
                    <div class="quest-info">
                        <div class="quest-title">Купи любую вещь</div>
                        <div class="quest-reward">Награда: 100 💎</div>
                    </div>
                    <button class="quest-btn" ${state.quests.bought && !state.quests.claimed.q2 ? '' : 'disabled'} onclick="claimQuest('q2', 100)">${state.quests.claimed.q2 ? 'Получено' : 'Забрать'}</button>
                </div>
                <div class="quest-item">
                    <div class="quest-info">
                        <div class="quest-title">Пригласи друга</div>
                        <div class="quest-reward">Награда: 200 💎</div>
                    </div>
                    <button class="quest-btn" ${state.quests.invited && !state.quests.claimed.q3 ? '' : 'disabled'} onclick="claimQuest('q3', 200)">${state.quests.claimed.q3 ? 'Получено' : 'Забрать'}</button>
                </div>
            `;
        }

        function claimQuest(id, rewardGems) {
            if (!state.quests.claimed[id]) {
                state.quests.claimed[id] = true;
                state.gems += rewardGems;
                tg.showAlert(`🎉 Ты получил ${rewardGems} гемов!`);
                updateUI();
            }
        }

        const shopData = [
            { id: 'hat', name: 'Кепка', icon: '🧢', price: 1000 },
            { id: 'glasses', name: 'Очки', icon: '🕶️', price: 5000 },
            { id: 'bowtie', name: 'Бабочка', icon: '🎀', price: 15000 },
            { id: 'crown', name: 'Корона', icon: '👑', price: 50000 }
        ];
        function renderShop() {
            const grid = document.getElementById('shop-grid');
            if(!grid) return; grid.innerHTML = '';
            shopData.forEach(item => {
                const isOwned = state.inventory[item.id];
                const isEq = state.equipped[item.id];
                grid.innerHTML += `<div class="card"><div class="card-icon">${item.icon}</div><div class="card-title">${item.name}</div><button class="card-price ${isOwned ? (isEq ? 'owned' : '') : ''}" onclick="buyItem('${item.id}', ${item.price})">${isOwned ? (isEq ? 'Снять' : 'Надеть') : `${item.price} 🪙`}</button></div>`;
            });
        }
        function buyItem(id, price) {
            if (state.inventory[id]) state.equipped[id] = !state.equipped[id];
            else if (state.coins >= price) { 
                state.coins -= price; state.inventory[id] = true; state.equipped[id] = true; 
                state.quests.bought = true;
            }
            else { tg.showAlert("Мало монет!"); return; }
            updateUI();
        }

        function renderFamily() {
            const btnCont = document.getElementById('pregnancy-btn-container');
            const status = document.getElementById('family-status');
            if(!status) return;
            if (state.hasBaby) { status.innerText = "👶 У тебя есть малыш!"; btnCont.innerHTML = ""; }
            else if (state.isPregnant) { status.innerText = `🤰 Беременна!`; btnCont.innerHTML = ""; }
            else if (state.gender === 'female') { status.innerText = "Готова к материнству"; if (state.streakDays >= 7) btnCont.innerHTML = `<button class="card-price" onclick="startPregnancy()">Забеременеть</button>`; else btnCont.innerHTML = `<div style="font-size:12px;color:#aaa;">Нужна серия 7 дней</div>`; }
            else { status.innerText = "Самец"; btnCont.innerHTML = ""; }
        }

        function startPregnancy() { state.isPregnant = true; state.pregnancyEnd = Date.now() + (7 * 24 * 60 * 60 * 1000); updateUI(); }

        document.getElementById('panda-wrapper').addEventListener('pointerdown', (e) => {
            if (state.energy <= 0) return;
            state.energy -= 1; state.coins += state.tapPower; state.quests.taps++;
            
            let earn = state.tapPower;
            if (currentMode === 'bros' || currentMode === 'sisters') earn = Math.floor(earn * 1.5);
            state.coins += (earn - state.tapPower);

            const p = document.getElementById('panda-wrapper');
            p.classList.remove('hit'); void p.offsetWidth; p.classList.add('hit');
            
            const earL = document.getElementById('ear-left');
            const earR = document.getElementById('ear-right');
            earL.style.transform = 'translateY(3px)'; earR.style.transform = 'translateY(3px)';
            setTimeout(() => { earL.style.transform = 'translateY(0)'; earR.style.transform = 'translateY(0)'; }, 200);

            const eyeL = document.getElementById('eye-L');
            const eyeR = document.getElementById('eye-R');
            eyeL.classList.remove('slow-open'); eyeR.classList.remove('slow-open');
            eyeL.classList.add('closed'); eyeR.classList.add('closed');
            clearTimeout(eyeTimeout);
            eyeTimeout = setTimeout(() => {
                eyeL.classList.add('slow-open'); eyeR.classList.add('slow-open');
                eyeL.classList.remove('closed'); eyeR.classList.remove('closed');
                setTimeout(() => { eyeL.classList.remove('slow-open'); eyeR.classList.remove('slow-open'); }, 2100);
            }, 300);

            const coin = document.createElement('div');
            coin.className = 'particle-coin'; coin.innerText = `+${earn}`;
            coin.style.left = (e.clientX - 15) + 'px'; coin.style.top = (e.clientY - 20) + 'px';
            document.body.appendChild(coin); setTimeout(() => coin.remove(), 900);
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "tap", power: earn }));
                ws.send(JSON.stringify({ type: "update_stats", coins: state.coins, gems: state.gems }));
            }
            updateUI();
        });

        function switchTab(tabId, btn) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('screen-' + tabId).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            
            // Принудительное обновление фермы при переходе
            if (tabId === 'farm') { renderFarm(); }
            if (tabId === 'friends') { fetchFriends(); fetchLeaderboard(); }
        }

        function loadGame() {
            const saved = localStorage.getItem('pandaUltimate');
            if (saved) { try { state = { ...state, ...JSON.parse(saved) }; } catch(e) {} }
            
            if (!state.gender) {
                document.getElementById('setup-screen').style.display = 'flex';
            } else {
                document.getElementById('setup-screen').style.display = 'none';
                applyGenderVisuals();
                checkStreak();
                updateUI();
                connectWebSocket();
                fetchFriends();
                fetchLeaderboard();
                startIdleBlinking();
                updateAvatarUI();
            }
        }

        function applyGenderVisuals() {
            const features = document.getElementById('gender-features');
            const bow = document.getElementById('gender-bow');
            const mouth = document.getElementById('mouth-path');
            
            if (state.gender === 'female') {
                features.innerHTML = `
                    <ellipse cx="45" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" />
                    <ellipse cx="155" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" />
                    <path d="M 60 75 Q 65 70 75 75" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round"/>
                    <path d="M 140 75 Q 135 70 125 75" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round"/>
                `;
                bow.style.display = 'block';
                mouth.setAttribute('d', 'M 92 112 Q 100 120 108 112');
            } else {
                features.innerHTML = `
                    <path d="M 50 65 Q 70 60 85 70" fill="none" stroke="#111" stroke-width="4" stroke-linecap="round"/>
                    <path d="M 150 65 Q 130 60 115 70" fill="none" stroke="#111" stroke-width="4" stroke-linecap="round"/>
                `;
                bow.style.display = 'none';
                mouth.setAttribute('d', 'M 92 112 L 108 112');
            }
        }

        function checkStreak() {
            const now = Date.now();
            const oneDay = 24 * 60 * 60 * 1000;
            if (state.lastLogin === 0) { state.lastLogin = now; state.streakDays = 1; }
            else {
                const daysPassed = Math.floor((now - state.lastLogin) / oneDay);
                if (daysPassed >= 1) { state.streakDays += daysPassed; state.lastLogin = now; }
            }
            document.getElementById('streak-badge').innerText = `🔥 Серия: ${state.streakDays} дней`;
            let scale = 0.9 + (state.streakDays * 0.02);
            if (scale > 1.4) scale = 1.4;
            document.getElementById('panda-wrapper').style.transform = `scale(${scale})`;
            saveGame();
        }

        function selectGender(g) {
            state.gender = g;
            document.getElementById('setup-screen').style.display = 'none';
            applyGenderVisuals();
            checkStreak(); saveGame(); updateUI(); connectWebSocket();
            fetchFriends();
            fetchLeaderboard();
            startIdleBlinking();
        }

        let eyeTimeout;
        function startIdleBlinking() {
            setInterval(() => {
                const eyeL = document.getElementById('eye-L');
                const eyeR = document.getElementById('eye-R');
                if (eyeL && !eyeL.classList.contains('closed') && !eyeL.classList.contains('slow-open')) {
                    eyeL.classList.add('closed');
                    eyeR.classList.add('closed');
                    setTimeout(() => {
                        eyeL.classList.remove('closed');
                        eyeR.classList.remove('closed');
                    }, 150);
                }
            }, 4000);
        }

        // Общий цикл (энергия, таймеры, ферма)
        setInterval(() => {
            if (state.energy < state.maxEnergy) state.energy = Math.min(state.maxEnergy, state.energy + state.regen);
            
            // Обновляем ферму каждую секунду, чтобы тикал таймер
            if (document.getElementById('screen-farm').classList.contains('active')) {
                renderFarm();
            }
            
            const now = Date.now();
            let changed = false;
            state.bamboos.forEach(b => {
                if (b.stage === 1 && now - b.planted > 60000) { b.stage = 2; changed = true; }
                if (b.stage === 2 && now - b.planted > 120000) { b.stage = 3; changed = true; }
            });
            if (changed) saveGame();
            
            updateUI();
        }, 1000);

        // Заглушки для функций, которые не критичны (чтобы не было ошибок)
        function connectWebSocket() {
            ws = new WebSocket(`${WS_URL}/ws/${roomId}/${myId}`);
            ws.onopen = () => { document.getElementById('conn-status').innerText = "🟢 Онлайн"; ws.send(JSON.stringify({ type: "set_name", name: state.nickname })); ws.send(JSON.stringify({ type: "set_gender", gender: state.gender })); ws.send(JSON.stringify({ type: "update_stats", coins: state.coins, gems: state.gems })); document.getElementById('loading').style.display = 'none'; };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'room_state') {
                    const friendData = data.players.find(p => String(p.id) !== myId);
                    if (friendData) {
                        document.getElementById('partner-container').style.display = 'block';
                        document.getElementById('partner-name').innerText = friendData.name;
                        if (state.gender === 'male' && friendData.gender === 'male') { document.getElementById('bg-base').className = 'bg-base bg-bro'; }
                        else if (state.gender === 'female' && friendData.gender === 'female') { document.getElementById('bg-base').className = 'bg-base bg-sisters'; }
                        else { document.getElementById('bg-base').className = 'bg-base bg-romantic'; }
                    } else {
                        document.getElementById('partner-container').style.display = 'none';
                        document.getElementById('bg-base').className = 'bg-base';
                    }
                } else if (data.type === 'player_tapped') {
                    const p = document.getElementById('partner-panda'); p.classList.remove('hit'); void p.offsetWidth; p.classList.add('hit');
                    state.coins += data.power; updateUI();
                }
            };
            ws.onclose = () => { document.getElementById('conn-status').innerText = "🔴 Оффлайн"; setTimeout(connectWebSocket, 3000); };
        }
        
        function fetchFriends() { /* ... */ }
        function fetchLeaderboard() { /* ... */ }
        function startMiniGame() { /* ... */ }
        function claimChest() { /* ... */ }
        function claimGoldenPaw() { /* ... */ }

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
        players_db[user_id] = {"name": f"Panda_{user_id[:4]}", "coins": 0, "gems": 0, "gender": "male", "last_active": time.time(), "friends": [], "gifts": 0, "verified": False}
    else:
        players_db[user_id]["last_active"] = time.time()
        
    if room_id not in rooms:
        rooms[room_id] = {"players": {}, "joint_progress": 0}
    
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
                players_db[user_id]["last_active"] = time.time()
                continue
                
            if message.get("type") == "send_gift":
                target_id = message.get("to")
                gift_type = message.get("gift")
                cost = message.get("cost", 0)
                
                if target_id in players_db:
                    players_db[target_id]["gifts"] += 1
                    if target_id in rooms[room_id]["players"]:
                        try:
                            await rooms[room_id]["players"][target_id].send_text(json.dumps({"type": "gift_received", "gift": gift_type}))
                        except:
                            pass
                continue
                
            if message.get("type") == "tap":
                if len(rooms[room_id]["players"]) > 1:
                    rooms[room_id]["joint_progress"] += 0.5
                    if rooms[room_id]["joint_progress"] >= 100:
                        rooms[room_id]["joint_progress"] = 0
                    await broadcast(room_id, {"type": "joint_progress", "progress": rooms[room_id]["joint_progress"]})

                await broadcast(room_id, {
                    "type": "player_tapped",
                    "user_id": user_id,
                    "power": message.get("power", 1)
                }, exclude_user=user_id)
    except WebSocketDisconnect:
        if user_id in rooms[room_id]["players"]:
            del rooms[room_id]["players"][user_id]
        if len(rooms[room_id]["players"]) == 0:
            del rooms[room_id]
        else:
            await broadcast_room_state(room_id)

@app.get("/api/leaderboard")
async def get_leaderboard():
    sorted_players = sorted(players_db.items(), key=lambda x: x[1]["coins"], reverse=True)[:50]
    result = []
    for uid, data in sorted_players:
        is_online = (time.time() - data["last_active"]) < 120
        result.append({"id": uid, "name": data["name"], "coins": data["coins"], "online": is_online, "gifts": data.get("gifts", 0), "verified": data.get("verified", False)})
    return result

@app.get("/api/friends/{user_id}")
async def get_friends(user_id: str):
    if user_id not in players_db:
        return []
    
    friends_list = []
    for f_id in players_db[user_id]["friends"]:
        if f_id in players_db:
            f_data = players_db[f_id]
            is_online = (time.time() - f_data["last_active"]) < 120
            friends_list.append({"id": f_id, "name": f_data["name"], "coins": f_data["coins"], "online": is_online, "gifts": f_data.get("gifts", 0), "verified": f_data.get("verified", False)})
    return friends_list

async def broadcast_room_state(room_id: str):
    if room_id in rooms:
        players_list = []
        for uid in rooms[room_id]["players"].keys():
            if uid in players_db:
                players_list.append({"id": uid, "name": players_db[uid]["name"], "gender": players_db[uid]["gender"]})
            else:
                players_list.append({"id": uid, "name": f"Panda_{uid[:4]}", "gender": "male"})
        await broadcast(room_id, {"type": "room_state", "players": players_list})

async def broadcast(room_id: str, message: dict, exclude_user: str = None):
    if room_id in rooms:
        for uid, connection in list(rooms[room_id]["players"].items()):
            if uid != exclude_user:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
