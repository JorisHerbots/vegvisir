import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import axios from 'axios';
import { waitForOpenConnection, sendMessage } from '@/stores/WebSocketSender';


export const useWebSocketStore = defineStore('websocket', () => {
    const websocket = ref<WebSocket>(new WebSocket("ws://127.0.0.1:5000/WebSocket"));

    function sendOnWebSocket(message: string) {
        sendMessage(websocket.value, message);        
    }

  return { websocket, sendOnWebSocket }

})