import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import { waitForOpenConnection, sendMessage } from '@/stores/WebSocketSender';
import { useWebSocketStore } from '@/stores/UseWebSocketStore';

interface ImagesDictionary {
  [key: string]: string[]}


export const usePasswordStore = defineStore('password', () => {
  const password_is_set = ref<boolean>(false);
  const websocketStore = useWebSocketStore();

  function encode_messagetype(message_type : string) : string {
    return websocketStore.message_type_to_header[message_type];
  }

  function decode_header(header : string) : string {
    return websocketStore.header_to_message_type[header]
  }
  websocketStore.sendOnWebSocket(encode_messagetype("password_is_set") + " : ");
    websocketStore.websocket.addEventListener('message', function (event : any) {

      let split = [event.data.slice(0, 3), event.data.slice(5)];
      let header = split[0]
      let message_type = decode_header(header)

      let message = split[1]


      if (message_type === "password_set_status") {
        if (message == " notset") {
          password_is_set.value = false
        }
        else {
          password_is_set.value = true
        }
      }
    }.bind(this));

  function isPasswordSet() {
    websocketStore.sendOnWebSocket(encode_messagetype("password_is_set") + " : ");
  }

  function setPassword(password: string) {
    websocketStore.sendOnWebSocket(encode_messagetype("password_set") + " : " + password);
  }

  return {setPassword, isPasswordSet, password_is_set}
})