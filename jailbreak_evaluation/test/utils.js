// 使用 fetch 发送 POST 请求启动工作流
async function startWorkflow() {
    try {
        // 启动 WebSocket 连接
        const wsConnected = await connectWebSocket();
        if (!wsConnected) {
            console.error('WebSocket 连接失败，停止后续操作');
            return;
        }

        const response = await fetch('http://127.0.0.1:8000/api/jailbreak-evaluation/workflow-start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                "project_id": 1 ,
                "model_name": "deepseek",
                "ev_time": "2025/03/22",
                "mode": 3
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`启动工作流失败: ${errorData.error || '未知错误'}`);
        }

        const data = await response.json();
        console.log('工作流启动成功:', data);

    } catch (error) {
        console.error('Error:', error);
    }
}

// 连接 WebSocket 并监听消息
function connectWebSocket(task_id='default') {
    return new Promise((resolve, reject) => {
        const wsUrl = `ws://127.0.0.1:8000/ws/jailbreak_evaluation/${task_id}/`;
        const socket = new WebSocket(wsUrl);

        socket.onopen = function() {
            console.log('WebSocket 连接已建立');
            resolve(true);
        };

        socket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            console.log('收到消息:', message);

            // 在页面上显示消息
            displayMessage(message);
        };

        socket.onclose = function() {
            console.log('WebSocket 连接已关闭');
            resolve(false);
        };

        socket.onerror = function(error) {
            console.error('WebSocket 错误:', error);
            resolve(false);
        };
    });
}

// 显示消息的函数
function displayMessage(message) {
    const messageContainer = document.getElementById('message-container');
    const messageElement = document.createElement('div');
    messageElement.textContent = JSON.stringify(message, null, 2);
    messageContainer.appendChild(messageElement);
}