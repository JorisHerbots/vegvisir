import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import axios from 'axios';
import { waitForOpenConnection, sendMessage } from '@/stores/WebSocketSender';


export const useWebSocketStore = defineStore('websocket', () => {
    const websocket = ref<WebSocket>(new WebSocket("ws://127.0.0.1:5000/WebSocket"));

    const inverse_dictionary = obj => Object.fromEntries(Object.entries(obj).map(a => a.reverse()))

    const message_type_to_header : {[key: string] : string} = {
      // Test related
      "add_test": "ADD",
      "remove_test": "REM",
      "update_test": "UPD",
      "progress_update": "PRO",
      "request_all_logfiles": "RAL",
      "update_all_logfiles": "UAL",
      "request_logfiles_in_folder": "RLF",
      "request_status_update": "RSU",
  
      // Imageset related 
      "imagesets_request_available": "IRA",
      "imagesets_request_loaded": "IRL",
      "imagesets_update_available": "IUA",
      "imagesets_update_loaded": "IUL",
      "imagesets_request_images": "IRI",
      "imagesets_update_images": "IUI",
      "imagesets_load_imageset": "ILI",
      "imagesets_remove_imageset": "IRR",
      "imagesets_activate_imageset": "IAI",
      "imagesets_disable_imageset": "IDI",
      "imageset_request_create": "IRC",
      "imageset_request_export": "IRE",

      // Implementations related
      "implementations_request": "IMR",
      "implementations_update": "IMU",
      "implementations_testcases_request": "ITR",
      "implementations_testcases_update": "ITU"
    } 

    const header_to_message_type : {[key: string] : string} = inverse_dictionary(message_type_to_header)

    function sendOnWebSocket(message: string) {
        sendMessage(websocket.value, message);        
    }

  return { websocket, sendOnWebSocket, message_type_to_header, header_to_message_type }

})