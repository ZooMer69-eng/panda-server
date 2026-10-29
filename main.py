from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Dict, List
import json
import os
import time

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
    <title>Panda Game 10.0</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Nunito', sans-serif; user-select: none; -webkit-tap-highlight-color: transparent; }
        body { background: #0a120e; color: #fff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; position: relative; }

        /* Экраны выбора пола */
        #setup-screen { position: fixed; inset: 0; background: rgba(10, 18, 14, 0.98); z-index: 9999; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }
        #setup-screen h1 { font-size: 28px; margin-bottom: 10px; color: #ffd700; }
        .gender-btns { display: flex; gap: 20px; margin-top: 20px; }
        .gender-btn { background: rgba(255,255,255,0.1); border: 2px solid #4caf50; border-radius: 20px; padding: 20px 30px; cursor: pointer; transition: 0.2s; }
        .gender-btn:hover { background: rgba(76, 175, 80, 0.3); transform: scale(1.05); }
        .gender-btn .icon { font-size: 50px; display: block; margin-bottom: 10px; }

        /* Фоны для разных режимов */
        .bg-base { position: absolute; inset: 0; z-index: 1; background: linear-gradient(180deg, #0b1712 0%, #143624 40%, #295d3b 70%, #346e42 100%); transition: background 1.5s; }
        .bg-romantic { background: linear-gradient(180deg, #2d1b36 0%, #6b3f5c 40%, #a86b7e 70%, #d9a0a8 100%) !important; }
        .bg-bro { background: linear-gradient(180deg, #1a1a2e 0%, #2d2d4a 40%, #4a3b52 70%, #6b4c5a 100%) !important; }
        .bg-sisters { background: linear-gradient(180deg, #361b2d 0%, #5c3f6b 40%, #7ea8a8 70%, #a8d9d9 100%) !important; }
        
        .bg-bamboo { position: absolute; bottom: 0; left: 0; width: 100%; height: 80%; display: flex; justify-content: space-around; z-index: 1; opacity: 0.6; pointer-events: none; }
        .stalk { position: relative; width: 14px; background: linear-gradient(90deg, #2e6e42 0%, #4ea868 50%, #2e6e42 100%); border-radius: 6px; bottom: 0; box-shadow: 2px 0 8px rgba(0,0,0,0.4); }
        .stalk::before { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(180deg, transparent 0 80px, #1f4d2e 80px 84px); border-radius: 6px; }
        .stalk::after { content: ''; position: absolute; top: 20%; left: 10px; width: 30px; height: 10px; background: #4ea868; border-radius: 4px 10px 0 4px; transform: rotate(-30deg); }
        .bg-grass { position: absolute; bottom: 0; left: 0; width: 100%; height: 15%; background: linear-gradient(to top, #0d1f14 0%, #173723 60%, transparent 100%); z-index: 2; pointer-events: none; }

        /* Хедер */
        .header { padding: 12px 15px; display: flex; justify-content: space-between; align-items: flex-start; z-index: 10; position: relative; }
        .rank-box { display: flex; flex-direction: column; gap: 4px; }
        .streak-badge { background: rgba(0,0,0,0.6); color: #ff6b00; padding: 4px 12px; border-radius: 15px; font-size: 11px; font-weight: 900; border: 1px solid #ff6b00; }
        
        .balance-container { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
        .balance { font-size: 28px; font-weight: 900; color: #fff; text-shadow: 2px 2px 8px rgba(0,0,0,0.8); display: flex; align-items: center; gap: 6px; }
        .edit-name-btn { background: rgba(255,255,255,0.2); border: none; border-radius: 50%; width: 24px; height: 24px; display: flex; justify-content: center; align-items: center; cursor: pointer; color: #fff; font-size: 12px; }
        
        .energy-box { display: flex; flex-direction: column; align-items: flex-end; }
        .energy-text { font-size: 11px; font-weight: 700; color: #fff; margin-bottom: 3px; }
        .energy-bar { width: 100px; height: 10px; background: rgba(0,0,0,0.5); border-radius: 5px; overflow: hidden; border: 1px solid rgba(255,255,255,0.4); }
        .energy-fill { height: 100%; background: linear-gradient(90deg, #00e5ff, #007bff); width: 100%; transition: width 0.3s; }

        /* Экраны */
        .screens { flex: 1; position: relative; z-index: 5; overflow: hidden; }
        .screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: none; flex-direction: column; }
        .screen.active { display: flex; }

        /* Тап */
        .tap-area { flex: 1; display: flex; justify-content: center; align-items: center; gap: 20px; position: relative; padding-bottom: 20px; }
        .panda-wrapper { position: relative; width: 190px; height: 210px; transform-origin: center bottom; cursor: pointer; transition: transform 1s ease-in-out; z-index: 5; }
        .panda-wrapper.partner-panda { width: 140px; height: 160px; opacity: 0.9; pointer-events: none; }
        .panda-wrapper:active { transform: scale(0.95); }
        .panda-wrapper.hit { animation: jump 0.25s ease-out; }
        @keyframes jump { 0% { transform: translateY(0); } 30% { transform: translateY(-15px) scale(1.05); } 100% { transform: translateY(0); } }
        
        /* Никнеймы */
        .panda-name { 
            text-align: center; font-size: 13px; font-weight: 900; color: #fff; margin-top: 8px; 
            text-shadow: 2px 2px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; 
            position: relative; z-index: 5; max-width: 140px; margin-left: auto; margin-right: auto;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            background: rgba(0,0,0,0.4); padding: 2px 8px; border-radius: 10px;
        }

        /* Анимация глаз */
        .eye { transform-box: fill-box; transform-origin: center; transition: transform 0.15s ease-in-out; }
        .eye.closed { transform: scaleY(0.1); }
        .eye.slow-open { transition: transform 2s ease-out; }

        /* Общая полоска прогресса */
        .joint-bar-container { width: 80%; margin: 10px auto; background: rgba(0,0,0,0.5); border-radius: 10px; overflow: hidden; display: none; position: relative; height: 22px; border: 1px solid rgba(255,255,255,0.2); z-index: 10; }
        .joint-bar-fill { height: 100%; background: linear-gradient(90deg, #ff416c, #ff4b2b); width: 0%; transition: width 0.3s; }
        .joint-bar-text { position: absolute; width: 100%; text-align: center; font-size: 12px; font-weight: 900; top: 2px; text-shadow: 1px 1px 2px #000; }

        /* Эффекты */
        .particle-coin { position: absolute; font-size: 24px; font-weight: 900; color: #ffd700; pointer-events: none; animation: popCoin 0.9s ease-out forwards; z-index: 20; text-shadow: 0 0 10px #ffd700; }
        @keyframes popCoin { 0% { transform: translateY(0) scale(0.4); opacity: 1; } 100% { transform: translateY(-100px) scale(1.2); opacity: 0; } }
        
        #golden-paw { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 50px; cursor: pointer; z-index: 100; display: none; animation: pulseGold 1s infinite alternate; }
        @keyframes pulseGold { 0% { transform: translate(-50%, -50%) scale(1); } 100% { transform: translate(-50%, -50%) scale(1.2); filter: drop-shadow(0 0 20px gold); } }

        /* Контент */
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
        .friend-item { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.05); padding: 10px 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
        .friend-info { display: flex; align-items: center; gap: 10px; }
        .friend-status { width: 10px; height: 10px; border-radius: 50%; }
        .status-online { background: #4caf50; box-shadow: 0 0 5px #4caf50; }
        .status-offline { background: #555; }
        .friend-name { font-weight: 900; font-size: 14px; }
        .friend-coins { font-size: 12px; color: #ffd700; }
        
        .tabs-sub { display: flex; gap: 10px; margin-bottom: 15px; }
        .tab-btn { flex: 1; background: rgba(255,255,255,0.1); border: none; color: #aaa; padding: 8px; border-radius: 8px; font-weight: 900; cursor: pointer; }
        .tab-btn.active { background: #4caf50; color: #fff; }

        .leaderboard-item { display: flex; justify-content: space-between; padding: 8px 15px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 14px; }
        .leaderboard-item span:first-child { font-weight: 900; color: #ffd700; width: 30px; }

        /* Навигация */
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
        .modal-box { background: #1a2e22; border: 2px solid #4caf50; border-radius: 20px; padding: 25px; width: 90%; max-width: 350px; }
        
        /* Поле ввода для ника */
        .name-input { width: 100%; padding: 10px; border-radius: 8px; border: none; font-size: 16px; font-weight: 900; text-align: center; margin-bottom: 15px; background: #fff; color: #111; }

        #error-log { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255,0,0,0.9); color: white; padding: 10px; font-size: 12px; z-index: 9999; display: none; word-break: break-all; }
        #debug-info { position: absolute; bottom: 2px; width: 100%; text-align: center; font-size: 10px; color: #555; z-index: 50; }
        #loading { position: fixed; inset: 0; background: #0a120e; z-index: 10000; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 20px; font-weight: 900; color: #4caf50; }
        #loading-text { margin-top: 20px; font-size: 14px; color: #aaa; text-align: center; }
        
        /* Квесты */
        .quest-item { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #ffd700; }
        .quest-info { flex: 1; }
        .quest-title { font-size: 14px; font-weight: 900; margin-bottom: 4px; }
        .quest-reward { font-size: 12px; color: #4caf50; font-weight: 900; }
        .quest-btn { background: #4caf50; color: #fff; border: none; padding: 8px 15px; border-radius: 8px; font-weight: 900; cursor: pointer; }
        .quest-btn:disabled { background: #555; cursor: not-allowed; }
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

    <!-- Модалка Смены Ника -->
    <div class="modal" id="name-modal">
        <div class="modal-box">
            <h2 style="color:#4caf50; margin-bottom:15px;">Твой Никнейм</h2>
            <input type="text" id="name-input" class="name-input" maxlength="15" placeholder="Введи имя...">
            <button class="card-price" style="background:#4caf50; color:#fff; padding:12px;" onclick="saveName()">Сохранить</button>
            <button class="card-price" style="background:#555; color:#fff; margin-top:10px;" onclick="closeModal('name-modal')">Отмена</button>
        </div>
    </div>

    <div class="modal" id="bandit-modal">
        <div class="modal-box">
            <h2 style="color:#f44336;">👹 Браконьер!</h2>
            <p>Быстро тапай по врагу!</p>
            <div style="font-size: 80px; cursor: pointer; transition: transform 0.1s;" id="bandit-icon" onclick="hitBandit()">👺</div>
            <div style="width: 100%; height: 10px; background: #333; border-radius: 5px; margin-top: 10px; overflow: hidden;">
                <div id="bandit-timer" style="height: 100%; background: #f44336; width: 100%; transition: width 0.1s linear;"></div>
            </div>
        </div>
    </div>

    <div class="modal" id="chest-modal">
        <div class="modal-box" style="text-align:center;">
            <h2 style="color:#ffd700;">🎁 Сундук дня!</h2>
            <div style="font-size: 60px; margin: 20px 0;">📦</div>
            <button class="card-price" style="background:#4caf50; color:#fff; font-size:16px; padding:15px;" onclick="claimChest()">Открыть</button>
        </div>
    </div>

    <div class="bg-base" id="bg-base"></div>
    
    <div class="bg-bamboo">
        <div class="stalk" style="height: 70%; left: 5%;"></div>
        <div class="stalk" style="height: 90%; left: 20%;"></div>
        <div class="stalk" style="height: 60%; right: 15%;"></div>
        <div class="stalk" style="height: 80%; right: 5%;"></div>
    </div>
    <div class="bg-grass"></div>

    <div class="header">
        <div class="rank-box">
            <div class="streak-badge" id="streak-badge">🔥 Серия: 0 дней</div>
            <div class="balance-container">
                <div class="balance"><span id="coins">0</span> 🪙</div>
                <button class="edit-name-btn" onclick="openNameModal()">✏️</button>
            </div>
        </div>
        <div class="energy-box">
            <div class="energy-text"><span id="energy">1000</span> / <span id="max-energy">1000</span> ⚡</div>
            <div class="energy-bar"><div class="energy-fill" id="energy-fill"></div></div>
            <div style="font-size:10px; color:#fff; margin-top:5px;" id="conn-status">Подключение...</div>
        </div>
    </div>

    <!-- Полоска совместного прогресса -->
    <div class="joint-bar-container" id="joint-bar">
        <div class="joint-bar-fill" id="joint-bar-fill"></div>
        <div class="joint-bar-text" id="joint-bar-text">Общее гнездышко: 0%</div>
    </div>

    <div class="screens">
        <div class="screen active" id="screen-tap">
            <div class="tap-area">
                <div id="golden-paw" onclick="claimGoldenPaw()">🐾</div>
                
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
                                    <path class="belly-pregnant" d="M 40 160 Q 100 110 160 160 Q 150 205 100 208 Q 50 205 40 160 Z" fill="url(#bellyGrad)" style="display:none;" />
                                </g>
                                <g class="head" transform="translate(0, -5)">
                                    <g id="ear-left"><circle cx="45" cy="45" r="20" fill="#1a1a1a" /><circle cx="45" cy="45" r="10" fill="#333" /></g>
                                    <g id="ear-right"><circle cx="155" cy="45" r="20" fill="#1a1a1a" /><circle cx="155" cy="45" r="10" fill="#333" /></g>
                                    
                                    <ellipse cx="100" cy="90" rx="65" ry="58" fill="url(#bodyGrad)" />
                                    
                                    <ellipse cx="70" cy="85" rx="18" ry="23" fill="#111" /><ellipse cx="130" cy="85" rx="18" ry="23" fill="#111" />
                                    
                                    <g class="eye" id="eye-L">
                                        <circle cx="70" cy="85" r="9" fill="#fff" />
                                        <circle cx="70" cy="85" r="6" fill="#111" />
                                        <circle cx="67.5" cy="82.5" r="2.5" fill="#fff" />
                                    </g>
                                    <g class="eye" id="eye-R">
                                        <circle cx="130" cy="85" r="9" fill="#fff" />
                                        <circle cx="130" cy="85" r="6" fill="#111" />
                                        <circle cx="127.5" cy="82.5" r="2.5" fill="#fff" />
                                    </g>
                                    
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
            <div id="debug-info"></div>
        </div>

        <div class="screen" id="screen-farm">
            <div class="content">
                <div class="section-title">Ферма бамбука 🎋</div>
                <div class="grid" id="farm-grid"></div>
            </div>
        </div>

        <div class="screen" id="screen-friends">
            <div class="content">
                <div class="section-title">Друзья 👥</div>
                
                <div class="tabs-sub">
                    <button class="tab-btn active" onclick="switchFriendsTab('list', this)">Мои друзья</button>
                    <button class="tab-btn" onclick="switchFriendsTab('top', this)">Топ 50</button>
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

        <div class="screen" id="screen-family">
            <div class="content">
                <div class="section-title">Семья 👨‍👩‍👧‍👦</div>
                <div class="card" style="margin-bottom:15px; padding:20px;">
                    <div id="family-status" style="font-size:16px; font-weight:900; color:#ffd700; margin-bottom:10px;">Ты пока один</div>
                    <div id="pregnancy-btn-container"></div>
                </div>
            </div>
        </div>

        <div class="screen" id="screen-shop">
            <div class="content">
                <div class="section-title">Магазин 🛍️</div>
                <div class="grid" id="shop-grid"></div>
            </div>
        </div>

        <div class="screen" id="screen-games">
            <div class="content">
                <div class="section-title">Мини-игры 🏆</div>
                <div class="game-area-mini" id="game-area-mini"></div>
                <div style="text-align:center; font-size:24px; font-weight:900; margin-bottom:10px;">Счет: <span id="mini-score">0</span></div>
                <button class="card-price" id="mini-btn-bamboo" onclick="startMiniGame('bamboo')" style="background:#4caf50; color:#fff; font-size:16px; padding:15px; margin-bottom:10px;">Поймай бамбук 🎋</button>
                <button class="card-price" id="mini-btn-food" onclick="startMiniGame('food')" style="background:#ff9800; color:#fff; font-size:16px; padding:15px;">Покорми панду 🍎</button>
            </div>
        </div>

        <!-- НОВАЯ ВКЛАДКА: КВЕСТЫ -->
        <div class="screen" id="screen-quests">
            <div class="content">
                <div class="section-title">Квесты 📜</div>
                <div id="quests-list"></div>
            </div>
        </div>
    </div>

    <div class="bottom-nav">
        <button class="nav-btn active" onclick="switchTab('tap', this)"><span>👆</span>Панда</button>
        <button class="nav-btn" onclick="switchTab('quests', this)"><span>📜</span>Квесты</button>
        <button class="nav-btn" onclick="switchTab('friends', this)"><span>👥</span>Друзья</button>
        <button class="nav-btn" onclick="switchTab('family', this)"><span>👨‍👩‍👧</span>Семья</button>
        <button class="nav-btn" onclick="switchTab('farm', this)"><span>🌱</span>Ферма</button>
        <button class="nav-btn" onclick="switchTab('games', this)"><span>🎮</span>Игры</button>
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
            coins: 500, gender: null, streakDays: 1, lastLogin: 0,
            tapPower: 1, energy: 1000, maxEnergy: 1000, regen: 5,
            isPregnant: false, pregnancyEnd: 0, hasBaby: false,
            inventory: { hat: false, glasses: false, crown: false, bowtie: false },
            equipped: { hat: false, glasses: false, crown: false, bowtie: false },
            bamboos: [{ id: 1, stage: 0, planted: 0 }, { id: 2, stage: 0, planted: 0 }, { id: 3, stage: 0, planted: 0 }],
            lastMiniGame: 0, lastBandit: 0, lastPaw: 0, lastChest: 0,
            friends: [],
            nickname: '',
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

        // Загрузка ника
        let savedName = localStorage.getItem('pandaNickname');
        if (!savedName) {
            savedName = tg.initDataUnsafe?.user?.first_name || `Panda_${myId.substring(0,4)}`;
            localStorage.setItem('pandaNickname', savedName);
        }
        state.nickname = savedName;
        document.getElementById('my-name').innerText = state.nickname;

        function openNameModal() {
            document.getElementById('name-input').value = state.nickname;
            document.getElementById('name-modal').classList.add('active');
        }

        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }

        function saveName() {
            let newName = document.getElementById('name-input').value.trim();
            if (newName === '') newName = `Panda_${myId.substring(0,4)}`;
            if (newName.length > 15) newName = newName.substring(0, 15);
            
            state.nickname = newName;
            localStorage.setItem('pandaNickname', newName);
            document.getElementById('my-name').innerText = newName;
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "set_name", name: newName }));
            }
            closeModal('name-modal');
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
            }
        }

        function saveGame() { localStorage.setItem('pandaUltimate', JSON.stringify(state)); }

        function selectGender(g) {
            state.gender = g;
            document.getElementById('setup-screen').style.display = 'none';
            applyGenderVisuals();
            checkStreak(); saveGame(); updateUI(); connectWebSocket();
            fetchFriends();
            fetchLeaderboard();
            startIdleBlinking();
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

        function updateUI() {
            document.getElementById('coins').innerText = Math.floor(state.coins).toLocaleString();
            document.getElementById('energy').innerText = Math.floor(state.energy);
            document.getElementById('max-energy').innerText = state.maxEnergy;
            document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';

            ['hat', 'glasses', 'crown', 'bowtie'].forEach(item => {
                const el = document.getElementById('acc-' + item);
                if (el) el.style.display = state.equipped[item] ? 'block' : 'none';
            });

            renderFarm(); renderShop(); renderFamily(); renderQuests();
            
            if (state.isPregnant) {
                document.querySelector('.belly-normal').style.display = 'none';
                document.querySelector('.belly-pregnant').style.display = 'block';
                if (Date.now() >= state.pregnancyEnd) {
                    state.isPregnant = false; state.hasBaby = true;
                    document.querySelector('.belly-normal').style.display = 'block';
                    document.querySelector('.belly-pregnant').style.display = 'none';
                    tg.showAlert("🎉 Ура! У тебя родился малыш-панда!");
                }
            } else {
                document.querySelector('.belly-normal').style.display = 'block';
                document.querySelector('.belly-pregnant').style.display = 'none';
            }

            updateTimers();
            saveGame();
        }

        function updateTimers() {
            const now = Date.now();
            
            if (now - state.lastChest > 24 * 60 * 60 * 1000) {
                document.getElementById('chest-modal').classList.add('active');
            }

            if (now - state.lastPaw > 15 * 60 * 1000 && document.getElementById('golden-paw').style.display !== 'block') {
                document.getElementById('golden-paw').style.display = 'block';
                setTimeout(() => {
                    if(document.getElementById('golden-paw').style.display === 'block') {
                        document.getElementById('golden-paw').style.display = 'none';
                        state.lastPaw = Date.now();
                    }
                }, 5000);
            }

            if (now - state.lastBandit > 10 * 60 * 1000 && !document.getElementById('bandit-modal').classList.contains('active')) {
                startBandit();
            }

            const timeLeft = Math.ceil((5 * 60 * 1000 - (now - state.lastMiniGame)) / 1000);
            const btnB = document.getElementById('mini-btn-bamboo');
            const btnF = document.getElementById('mini-btn-food');
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

        // ================== КВЕСТЫ ==================
        function renderQuests() {
            const list = document.getElementById('quests-list');
            if (!list) return;
            
            list.innerHTML = `
                <div class="quest-item">
                    <div class="quest-info">
                        <div class="quest-title">Сделай 100 кликов</div>
                        <div class="quest-reward">Награда: 1000 🪙</div>
                        <div style="font-size:11px; color:#aaa;">Прогресс: ${Math.min(state.quests.taps, 100)}/100</div>
                    </div>
                    <button class="quest-btn" ${state.quests.taps >= 100 && !state.quests.claimed.q1 ? '' : 'disabled'} onclick="claimQuest('q1', 1000)">${state.quests.claimed.q1 ? 'Получено' : 'Забрать'}</button>
                </div>
                <div class="quest-item">
                    <div class="quest-info">
                        <div class="quest-title">Купи любую вещь в магазине</div>
                        <div class="quest-reward">Награда: 2000 🪙</div>
                        <div style="font-size:11px; color:#aaa;">Прогресс: ${state.quests.bought ? 'Выполнено' : '0/1'}</div>
                    </div>
                    <button class="quest-btn" ${state.quests.bought && !state.quests.claimed.q2 ? '' : 'disabled'} onclick="claimQuest('q2', 2000)">${state.quests.claimed.q2 ? 'Получено' : 'Забрать'}</button>
                </div>
                <div class="quest-item">
                    <div class="quest-info">
                        <div class="quest-title">Пригласи друга (поделись ссылкой)</div>
                        <div class="quest-reward">Награда: 5000 🪙</div>
                        <div style="font-size:11px; color:#aaa;">Прогресс: ${state.quests.invited ? 'Выполнено' : '0/1'}</div>
                    </div>
                    <button class="quest-btn" ${state.quests.invited && !state.quests.claimed.q3 ? '' : 'disabled'} onclick="claimQuest('q3', 5000)">${state.quests.claimed.q3 ? 'Получено' : 'Забрать'}</button>
                </div>
            `;
        }

        function claimQuest(id, reward) {
            if (!state.quests.claimed[id]) {
                state.quests.claimed[id] = true;
                state.coins += reward;
                tg.showAlert(`🎉 Ты получил ${reward} монет за квест!`);
                updateUI();
            }
        }

        // ================== API ==================
        async function fetchFriends() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);
                const res = await fetch(`${API_URL}/api/friends/${myId}`, { signal: controller.signal });
                clearTimeout(timeoutId);
                const data = await res.json();
                state.friends = data;
                renderFriends();
            } catch(e) { 
                console.log("Ошибка загрузки друзей:", e); 
                document.getElementById('friends-list').innerHTML = `<p style="text-align:center; color:#888;">Сервер просыпается. Подождите 10 секунд...</p>`;
            }
        }

        async function fetchLeaderboard() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);
                const res = await fetch(`${API_URL}/api/leaderboard`, { signal: controller.signal });
                clearTimeout(timeoutId);
                const data = await res.json();
                renderLeaderboard(data);
            } catch(e) { 
                console.log("Ошибка загрузки топа:", e); 
                document.getElementById('leaderboard-list').innerHTML = `<p style="text-align:center; color:#888;">Сервер просыпается. Подождите...</p>`;
            }
        }

        function renderFriends() {
            const list = document.getElementById('friends-list');
            if(!list) return;
            if (state.friends.length === 0) {
                list.innerHTML = `<p style="text-align:center; color:#888;">Пока нет друзей. Пригласи кого-нибудь!</p>`;
                return;
            }
            list.innerHTML = state.friends.map(f => `
                <div class="friend-item">
                    <div class="friend-info">
                        <div class="friend-status ${f.online ? 'status-online' : 'status-offline'}"></div>
                        <div>
                            <div class="friend-name">${f.name}</div>
                            <div class="friend-coins">${f.coins.toLocaleString()} 🪙</div>
                        </div>
                    </div>
                    <button style="background:none; border:none; font-size:20px; cursor:pointer;" onclick="sendGift('${f.name}')">🎁</button>
                </div>
            `).join('');
        }

        function renderLeaderboard(data) {
            const list = document.getElementById('leaderboard-list');
            if(!list) return;
            list.innerHTML = data.map((player, index) => `
                <div class="leaderboard-item">
                    <span>${index + 1}.</span>
                    <span style="flex:1; margin-left:10px;">${player.name} ${player.online ? '🟢' : ''}</span>
                    <span style="color:#ffd700;">${player.coins.toLocaleString()} 🪙</span>
                </div>
            `).join('');
        }

        function switchFriendsTab(tab, btn) {
            document.querySelectorAll('.tabs-sub .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
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

        function sendGift(friendName) {
            if (state.coins < 500) { tg.showAlert("Нужно 500 монет, чтобы отправить подарок!"); return; }
            state.coins -= 500; updateUI();
            tg.showAlert(`🎁 Ты подарил 500 монет другу ${friendName}!`);
        }

        function claimChest() {
            document.getElementById('chest-modal').classList.remove('active');
            state.lastChest = Date.now();
            const amt = Math.floor(Math.random() * 4500) + 500;
            state.coins += amt;
            tg.showAlert(`🎉 Ты получил ${amt} монет!`);
            updateUI();
        }

        function claimGoldenPaw() {
            document.getElementById('golden-paw').style.display = 'none';
            state.lastPaw = Date.now();
            const amt = Math.floor(Math.random() * 2000) + 1000;
            state.coins += amt;
            tg.showAlert(`🐾 Золотая лапа принесла ${amt} монет!`);
            updateUI();
        }

        function startBandit() {
            document.getElementById('bandit-modal').classList.add('active');
            let hits = 15;
            let time = 5.0;
            document.getElementById('bandit-timer').style.width = '100%';
            if(banditInterval) clearInterval(banditInterval);
            banditInterval = setInterval(() => {
                time -= 0.1;
                document.getElementById('bandit-timer').style.width = `${(time / 5) * 100}%`;
                if (time <= 0) {
                    clearInterval(banditInterval);
                    document.getElementById('bandit-modal').classList.remove('active');
                    state.lastBandit = Date.now();
                    const loss = Math.floor(state.coins * 0.05);
                    state.coins -= loss;
                    tg.showAlert(`💀 Браконьер украл ${loss} монет!`);
                    updateUI();
                }
            }, 100);
            document.getElementById('bandit-icon').onclick = () => {
                hits--;
                if (hits <= 0) {
                    clearInterval(banditInterval);
                    document.getElementById('bandit-modal').classList.remove('active');
                    state.lastBandit = Date.now();
                    state.coins += 2000;
                    tg.showAlert("🏆 Ты отбил панду! +2000 монет!");
                    updateUI();
                }
            };
        }

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
                state.quests.bought = true; // Выполняем квест
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
        
        function inviteFriend() {
            state.quests.invited = true; // Выполняем квест
            
            // ИСПОЛЬЗУЕМ ВСТРОЕННЫЙ ШАРИНГ TELEGRAM (надежнее чем navigator.clipboard)
            const link = `https://t.me/nash_sad_69_bot?startapp=${roomId}`; 
            const text = `Присоединяйся к моей игре с пандой!`;
            
            if (tg.openTelegramLink) {
                tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`);
            } else {
                navigator.clipboard.writeText(link).then(() => tg.showAlert("Ссылка скопирована! Отправь другу."));
            }
            updateUI();
        }

        let currentMode = 'solo';
        let jointProgress = 0;

        function connectWebSocket() {
            ws = new WebSocket(`${WS_URL}/ws/${roomId}/${myId}`);
            ws.onopen = () => {
                document.getElementById('conn-status').innerText = "🟢 Онлайн";
                ws.send(JSON.stringify({ type: "set_name", name: state.nickname }));
                ws.send(JSON.stringify({ type: "set_gender", gender: state.gender }));
                ws.send(JSON.stringify({ type: "update_stats", coins: state.coins }));
                document.getElementById('loading').style.display = 'none';
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'room_state') {
                    const myData = data.players.find(p => String(p.id) === myId);
                    const friendData = data.players.find(p => String(p.id) !== myId);
                    
                    if (myData) document.getElementById('my-name').innerText = myData.name;
                    
                    if (friendData) {
                        document.getElementById('partner-container').style.display = 'block';
                        document.getElementById('partner-name').innerText = friendData.name;
                        
                        // Определяем режим
                        if (state.gender === 'male' && friendData.gender === 'male') {
                            currentMode = 'bros';
                            document.getElementById('bg-base').className = 'bg-base bg-bro';
                            document.getElementById('joint-bar').style.display = 'block';
                        } else if (state.gender === 'female' && friendData.gender === 'female') {
                            currentMode = 'sisters';
                            document.getElementById('bg-base').className = 'bg-base bg-sisters';
                            document.getElementById('joint-bar').style.display = 'block';
                        } else {
                            currentMode = 'couple';
                            document.getElementById('bg-base').className = 'bg-base bg-romantic';
                            document.getElementById('joint-bar').style.display = 'block';
                        }
                    } else {
                        currentMode = 'solo';
                        document.getElementById('partner-container').style.display = 'none';
                        document.getElementById('bg-base').className = 'bg-base';
                        document.getElementById('joint-bar').style.display = 'none';
                    }
                    document.getElementById('debug-info').innerText = `Комната: ${roomId} | Игроков: ${data.players.length}`;
                } else if (data.type === 'player_tapped') {
                    const p = document.getElementById('partner-panda');
                    p.classList.remove('hit'); void p.offsetWidth; p.classList.add('hit');
                    state.coins += data.power; updateUI();
                } else if (data.type === 'joint_progress') {
                    jointProgress = data.progress;
                    document.getElementById('joint-bar-fill').style.width = jointProgress + '%';
                    document.getElementById('joint-bar-text').innerText = `Общее гнездышко: ${Math.floor(jointProgress)}%`;
                    if (jointProgress >= 100) {
                        state.coins += 10000;
                        jointProgress = 0;
                        tg.showAlert("🎉 Гнездышко свито! Вы оба получили по 10 000 монет!");
                        updateUI();
                    }
                }
            };
            ws.onclose = () => {
                document.getElementById('conn-status').innerText = "🔴 Оффлайн";
                setTimeout(connectWebSocket, 3000);
            };
            ws.onerror = (e) => { console.log("WebSocket error:", e); };
        }

        document.getElementById('panda-wrapper').addEventListener('pointerdown', (e) => {
            if (state.energy <= 0) return;
            state.energy -= 1; state.coins += state.tapPower;
            state.quests.taps++; // Считаем клики
            
            // Бонус братанов / сестер
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
                ws.send(JSON.stringify({ type: "update_stats", coins: state.coins }));
            }
            updateUI();
        });

        let miniScore = 0, miniActive = false;
        function startMiniGame(type) {
            if (miniActive || Date.now() - state.lastMiniGame < 5 * 60 * 1000) return; 
            miniActive = true; miniScore = 0; document.getElementById('mini-score').innerText = 0;
            state.lastMiniGame = Date.now(); saveGame();
            const area = document.getElementById('game-area-mini'); area.innerHTML = '';
            const interval = setInterval(() => {
                if (!miniActive) return;
                const b = document.createElement('div');
                b.className = 'falling-item'; 
                b.innerText = type === 'bamboo' ? '🎋' : (Math.random() > 0.5 ? '🍎' : '🍔');
                b.style.left = Math.random() * 80 + 10 + '%';
                b.style.animationDuration = (Math.random() * 1 + 1) + 's';
                b.onclick = () => { if(miniActive) { miniScore++; document.getElementById('mini-score').innerText = miniScore; b.remove(); } };
                area.appendChild(b); setTimeout(() => b.remove(), 2000);
            }, 300);
            setTimeout(() => {
                miniActive = false; clearInterval(interval);
                state.coins += miniScore * 100;
                tg.showAlert(`Игра окончена! Ты набрал ${miniScore} очков (+${miniScore * 100} монет).`);
                updateUI();
            }, 10000);
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('screen-' + tabId).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (tabId === 'friends') { fetchFriends(); fetchLeaderboard(); }
        }

        setInterval(() => {
            if (state.energy < state.maxEnergy) state.energy = Math.min(state.maxEnergy, state.energy + state.regenerate);
            const now = Date.now();
            let changed = false;
            state.bamboos.forEach(b => {
                if (b.stage === 1 && now - b.planted > 60000) { b.stage = 2; changed = true; }
                if (b.stage === 2 && now - b.planted > 120000) { b.stage = 3; changed = true; }
            });
            if (changed) saveGame();
            updateUI();
        }, 1000);

        try {
            loadGame();
        } catch(e) {
            alert("Ошибка при загрузке игры: " + e.message);
        }
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
        players_db[user_id] = {"name": f"Panda_{user_id[:4]}", "coins": 0, "gender": "male", "last_active": time.time(), "friends": []}
    else:
        players_db[user_id]["last_active"] = time.time()
        
    if room_id not in rooms:
        rooms[room_id] = {"players": {}, "joint_progress": 0}
    
    # Сохраняем друга при входе в комнату
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
                players_db[user_id]["last_active"] = time.time()
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
        result.append({"id": uid, "name": data["name"], "coins": data["coins"], "online": is_online})
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
            friends_list.append({"id": f_id, "name": f_data["name"], "coins": f_data["coins"], "online": is_online})
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

