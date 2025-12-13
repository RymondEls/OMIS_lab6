// Глобальные переменные
const videoCanvas = document.getElementById('videoCanvas');
const overlayCanvas = document.getElementById('overlayCanvas');
const vctx = videoCanvas.getContext('2d');
const octx = overlayCanvas.getContext('2d');
const statusEl = document.getElementById('status');
const videoStatusEl = document.getElementById('videoStatus');
const recognizedGestureEl = document.getElementById('recognizedGesture');
const actionResultEl = document.getElementById('actionResult');
const rulesListEl = document.getElementById('rulesList');
const analysisReportEl = document.getElementById('analysisReport');
const availableGesturesEl = document.getElementById('availableGestures');
const historyListEl = document.getElementById('historyList');
const actionTypeSelect = document.getElementById('actionType');
const startRecordingBtn = document.getElementById('startRecordingBtn');
const stopRecordingBtn = document.getElementById('stopRecordingBtn');

let ws = null;
let currentTab = 'user';
let recording = false;
let recordSequence = [];
let gestureMappings = {};
let recognitionHistory = [];

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    connectWS();
    switchTab('user');
    loadGestureMappings();
    setupActionTypeHandler();
    loadHistory();
});

// Переключение вкладок
function switchTab(tab) {
    // Скрыть все вкладки
    document.querySelectorAll('.tab').forEach(t => t.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    // Показать выбранную вкладку
    document.getElementById(tab + 'Tab').classList.remove('hidden');
    document.getElementById(tab + 'TabBtn').classList.add('active');
    
    currentTab = tab;
    statusEl.textContent = `Режим: ${getTabName(tab)}`;
    
    // Обновить контент вкладки
    if (tab === 'developer') {
        loadRules();
    } else if (tab === 'specialist') {
        loadHistory();
    }
}

function getTabName(tab) {
    const names = {
        'user': 'Пользователь',
        'developer': 'Разработчик',
        'specialist': 'Специалист'
    };
    return names[tab] || tab;
}

// WebSocket соединение
function connectWS() {
    const protocol = location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + location.host + '/capture/ws';
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        statusEl.textContent = 'Статус: Подключено';
        videoStatusEl.textContent = 'Камера активна';
        console.log('WebSocket подключен');
    };
    
    ws.onclose = () => {
        statusEl.textContent = 'Статус: Отключено. Переподключение...';
        videoStatusEl.textContent = 'Переподключение...';
        setTimeout(connectWS, 2000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket ошибка:', error);
        statusEl.textContent = 'Статус: Ошибка соединения';
    };
    
    ws.onmessage = async (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Отображение видео
            if (data.frame) {
                const img = new Image();
                img.onload = () => {
                    vctx.drawImage(img, 0, 0, 640, 480);
                };
                img.src = data.frame;
            }
            
            // Отрисовка скелета
            if (data.landmarks) {
                drawSkeleton(data.landmarks);
            }
            
            // Распознавание жеста
            if (data.landmarks && Object.keys(data.landmarks).length > 0) {
                await recognizeGesture(data.landmarks, data.timestamp);
            }
            
            // Запись последовательности
            if (recording) {
                recordSequence.push(data.landmarks);
            }
        } catch (error) {
            console.error('Ошибка обработки сообщения:', error);
        }
    };
}

// Отрисовка скелета
function drawSkeleton(landmarks) {
    octx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    
    if (!landmarks || Object.keys(landmarks).length === 0) {
        return;
    }
    
    // Соединения для MediaPipe Pose
    const connections = [
        // Плечи и руки
        [11, 13], [13, 15],  // Левая рука
        [12, 14], [14, 16],  // Правая рука
        [11, 12],            // Плечи
        [11, 23], [12, 24],  // Плечи к бедрам
        [23, 24],            // Бедра
        [0, 11], [0, 12],    // Голова к плечам
    ];
    
    // Отрисовка соединений
    octx.strokeStyle = '#00ffff';
    octx.lineWidth = 3;
    
    connections.forEach(([a, b]) => {
        const pointA = landmarks[`pose_${a}`];
        const pointB = landmarks[`pose_${b}`];
        
        if (pointA && pointB && 
            pointA.visibility > 0.5 && pointB.visibility > 0.5) {
            octx.beginPath();
            octx.moveTo(pointA.x * 640, pointA.y * 480);
            octx.lineTo(pointB.x * 640, pointB.y * 480);
            octx.stroke();
        }
    });
    
    // Отрисовка точек
    octx.fillStyle = '#00ff00';
    for (const key in landmarks) {
        const point = landmarks[key];
        if (point && point.visibility > 0.5) {
            octx.beginPath();
            octx.arc(point.x * 640, point.y * 480, 5, 0, Math.PI * 2);
            octx.fill();
        }
    }
}

// Распознавание жеста
async function recognizeGesture(landmarks, timestamp) {
    try {
        const response = await fetch('/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ landmarks, timestamp })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Обновление UI в режиме пользователя
        if (currentTab === 'user') {
            if (result.gesture && result.gesture !== 'none') {
                recognizedGestureEl.textContent = result.gesture;
                recognizedGestureEl.style.color = '#00ff00';
                
                // Отображение действия
                if (result.action) {
                    if (result.action.status === 'logged') {
                        actionResultEl.textContent = result.action.message || 'Действие выполнено';
                        actionResultEl.style.color = '#10b981';
                    } else if (result.action.status === 'callback_sent') {
                        actionResultEl.textContent = `Callback отправлен (код: ${result.action.code})`;
                        actionResultEl.style.color = '#3b82f6';
                    } else {
                        actionResultEl.textContent = result.action.message || JSON.stringify(result.action);
                        actionResultEl.style.color = '#f59e0b';
                    }
                }
            } else {
                recognizedGestureEl.textContent = 'Ожидание жеста...';
                recognizedGestureEl.style.color = '#999';
            }
        }
        
        // Сохранение в историю
        if (result.gesture && result.gesture !== 'none') {
            recognitionHistory.push({
                gesture: result.gesture,
                timestamp: timestamp || Date.now(),
                action: result.action
            });
            
            // Ограничение истории
            if (recognitionHistory.length > 50) {
                recognitionHistory.shift();
            }
        }
    } catch (error) {
        console.error('Ошибка распознавания жеста:', error);
    }
}

// Загрузка маппингов жестов
async function loadGestureMappings() {
    try {
        const response = await fetch('/settings/gestures');
        const data = await response.json();
        gestureMappings = data.mappings || {};
        updateAvailableGestures();
    } catch (error) {
        console.error('Ошибка загрузки маппингов:', error);
    }
}

// Обновление списка доступных жестов
function updateAvailableGestures() {
    availableGesturesEl.innerHTML = '';
    
    const gestures = Object.keys(gestureMappings);
    if (gestures.length === 0) {
        availableGesturesEl.innerHTML = '<p class="placeholder">Нет настроенных жестов</p>';
        return;
    }
    
    gestures.forEach(gesture => {
        const mapping = gestureMappings[gesture];
        const div = document.createElement('div');
        div.className = 'gesture-item';
        div.innerHTML = `
            <strong>${gesture}</strong><br>
            <small>${mapping.description || mapping.type || 'Без описания'}</small>
        `;
        availableGesturesEl.appendChild(div);
    });
}

// Обработчик изменения типа действия
function setupActionTypeHandler() {
    actionTypeSelect.addEventListener('change', (e) => {
        const type = e.target.value;
        
        // Скрыть все группы
        document.getElementById('messageGroup').classList.add('hidden');
        document.getElementById('urlGroup').classList.add('hidden');
        document.getElementById('keyGroup').classList.add('hidden');
        document.getElementById('mouseActionGroup').classList.add('hidden');
        
        // Показать нужную группу
        if (type === 'log') {
            document.getElementById('messageGroup').classList.remove('hidden');
        } else if (type === 'callback') {
            document.getElementById('urlGroup').classList.remove('hidden');
        } else if (type === 'keyboard') {
            document.getElementById('keyGroup').classList.remove('hidden');
        } else if (type === 'mouse') {
            document.getElementById('mouseActionGroup').classList.remove('hidden');
        }
    });
}

// Добавление правила жеста
async function addCustomRule() {
    const gesture = document.getElementById('gestureName').value.trim();
    const actionType = document.getElementById('actionType').value;
    
    if (!gesture) {
        alert('Введите название жеста');
        return;
    }
    
    const mapping = {
        gesture,
        action_type: actionType
    };
    
    if (actionType === 'log') {
        mapping.message = document.getElementById('actionMessage').value.trim();
    } else if (actionType === 'callback') {
        mapping.url = document.getElementById('actionUrl').value.trim();
    } else if (actionType === 'keyboard') {
        mapping.key = document.getElementById('actionKey').value.trim();
    } else if (actionType === 'mouse') {
        mapping.action = document.getElementById('mouseAction').value;
    }
    
    mapping.description = document.getElementById('actionDescription').value.trim();
    
    try {
        const response = await fetch('/settings/gestures', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mapping)
        });
        
        if (!response.ok) {
            throw new Error('Ошибка создания правила');
        }
        
        const result = await response.json();
        alert('Правило успешно создано!');
        
        // Очистка формы
        document.getElementById('gestureName').value = '';
        document.getElementById('actionMessage').value = '';
        document.getElementById('actionUrl').value = '';
        document.getElementById('actionKey').value = '';
        document.getElementById('actionDescription').value = '';
        
        // Обновление списков
        loadGestureMappings();
        loadRules();
    } catch (error) {
        console.error('Ошибка создания правила:', error);
        alert('Ошибка создания правила: ' + error.message);
    }
}

// Загрузка правил
async function loadRules() {
    try {
        const response = await fetch('/settings/gestures');
        const data = await response.json();
        gestureMappings = data.mappings || {};
        
        rulesListEl.innerHTML = '';
        
        if (Object.keys(gestureMappings).length === 0) {
            rulesListEl.innerHTML = '<p class="placeholder">Нет настроенных правил</p>';
            return;
        }
        
        Object.entries(gestureMappings).forEach(([gesture, mapping]) => {
            const div = document.createElement('div');
            div.className = 'rule-item';
            div.innerHTML = `
                <div class="rule-info">
                    <div class="rule-gesture">${gesture}</div>
                    <div class="rule-action">
                        Тип: ${mapping.type} | 
                        ${mapping.description || mapping.message || 'Без описания'}
                    </div>
                </div>
                <div class="rule-buttons">
                    <button class="btn-small btn-delete" onclick="deleteRule('${gesture}')">Удалить</button>
                </div>
            `;
            rulesListEl.appendChild(div);
        });
    } catch (error) {
        console.error('Ошибка загрузки правил:', error);
    }
}

// Удаление правила
async function deleteRule(gesture) {
    if (!confirm(`Удалить правило для жеста "${gesture}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/settings/gestures/${gesture}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка удаления правила');
        }
        
        loadGestureMappings();
        loadRules();
    } catch (error) {
        console.error('Ошибка удаления правила:', error);
        alert('Ошибка удаления правила: ' + error.message);
    }
}

// Начало записи
function startRecording() {
    const label = document.getElementById('exerciseLabel').value.trim();
    if (!label) {
        alert('Введите название упражнения');
        return;
    }
    
    recording = true;
    recordSequence = [];
    startRecordingBtn.disabled = true;
    stopRecordingBtn.disabled = false;
    
    document.getElementById('recordingStatus').classList.remove('hidden');
    statusEl.textContent = `Запись: ${label}`;
}

// Остановка записи и анализ
async function stopRecording() {
    if (!recording) {
        return;
    }
    
    recording = false;
    startRecordingBtn.disabled = false;
    stopRecordingBtn.disabled = true;
    
    document.getElementById('recordingStatus').classList.add('hidden');
    statusEl.textContent = 'Анализ...';
    
    const label = document.getElementById('exerciseLabel').value.trim();
    
    try {
        const response = await fetch('/record/sequence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                label,
                sequence: recordSequence,
                timestamp: Date.now() / 1000
            })
        });
        
        if (!response.ok) {
            throw new Error('Ошибка анализа');
        }
        
        const data = await response.json();
        displayAnalysisReport(data.report, label);
        loadHistory();
        statusEl.textContent = 'Анализ завершен';
    } catch (error) {
        console.error('Ошибка анализа:', error);
        alert('Ошибка анализа: ' + error.message);
        statusEl.textContent = 'Ошибка анализа';
    }
}

// Отображение отчета об анализе
function displayAnalysisReport(report, label) {
    analysisReportEl.innerHTML = `
        <h4>Отчет для упражнения: ${label}</h4>
        <div class="report-item">
            <div class="report-label">Среднее отклонение:</div>
            <div class="report-value">${report.avg_deviation.toFixed(4)}</div>
        </div>
        <div class="report-item">
            <div class="report-label">Максимальное отклонение:</div>
            <div class="report-value">${report.max_deviation.toFixed(4)}</div>
        </div>
        <div class="report-item">
            <div class="report-label">Минимальное отклонение:</div>
            <div class="report-value">${report.min_deviation.toFixed(4)}</div>
        </div>
        <div class="report-item">
            <div class="report-label">Оценка техники:</div>
            <div class="report-value">${report.progress_note}</div>
        </div>
        ${report.recognized_gestures && report.recognized_gestures.length > 0 ? `
            <div class="report-item">
                <div class="report-label">Распознанные жесты:</div>
                <div class="report-value">
                    ${report.recognized_gestures.map(g => `${g.gesture} (кадр ${g.frame})`).join(', ')}
                </div>
            </div>
        ` : ''}
        ${report.recommendations && report.recommendations.length > 0 ? `
            <div class="recommendations">
                <h4>Рекомендации:</h4>
                <ul>
                    ${report.recommendations.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        ` : ''}
    `;
}

// Очистка анализа
function clearAnalysis() {
    analysisReportEl.innerHTML = '<p class="placeholder">Запишите движение для получения отчета</p>';
    document.getElementById('exerciseLabel').value = '';
    recordSequence = [];
}

// Загрузка истории записей
async function loadHistory() {
    const label = document.getElementById('exerciseLabel')?.value.trim();
    if (!label) {
        historyListEl.innerHTML = '<p class="placeholder">Введите название упражнения для просмотра истории</p>';
        return;
    }
    
    try {
        const response = await fetch(`/record/sequences/${encodeURIComponent(label)}`);
        const data = await response.json();
        
        historyListEl.innerHTML = '';
        
        if (data.sequences.length === 0) {
            historyListEl.innerHTML = '<p class="placeholder">Нет записей для этого упражнения</p>';
            return;
        }
        
        data.sequences.forEach(seq => {
            const div = document.createElement('div');
            div.className = 'history-item';
            const date = new Date(seq.timestamp * 1000).toLocaleString('ru-RU');
            div.innerHTML = `
                <div>
                    <strong>${seq.filename}</strong><br>
                    <small>${date} | Отклонение: ${seq.avg_deviation?.toFixed(4) || 'N/A'}</small>
                </div>
            `;
            historyListEl.appendChild(div);
        });
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
    }
}

// Переключение темы
document.getElementById('themeToggle').addEventListener('click', () => {
    document.body.classList.toggle('dark');
    const btn = document.getElementById('themeToggle');
    btn.textContent = document.body.classList.contains('dark') ? '☀️ Светлая тема' : '🌙 Темная тема';
});
