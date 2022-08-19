import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import { waitForOpenConnection, sendMessage } from '@/stores/WebSocketSender';

interface ImagesDictionary {
  [key: string]: string[]
}


export const useImagesetsStore = defineStore('imagesets', () => {
  const imagesets_loaded = ref<string[]>([]);
  const imagesets_available = ref<string[]>([]);
  const imagesets_images = ref<ImagesDictionary>({})
  const websocket = ref<WebSocket>();

  const inverse_dictionary = obj => Object.fromEntries(Object.entries(obj).map(a => a.reverse()))

  const _message_type_to_header : {[key: string] : string} = {
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
    "imageset_request_export": "IRE"
  } 

  const _header_to_message_type : {[key: string] : string} = inverse_dictionary(_message_type_to_header)

  function encode_messagetype(message_type : string) : string {
    return _message_type_to_header[message_type];
  }

  function decode_header(header : string) : string {
    return _header_to_message_type[header]
  }
  
  websocket.value = new WebSocket("ws://127.0.0.1:5000/ImagesetsWebSocket");

    websocket.value.addEventListener('message', function (event) {

      let split = [event.data.slice(0, 3), event.data.slice(5)];
      let header = split[0]
      let message_type = decode_header(header)

      let message = split[1]

      if (message_type === "imagesets_update_available") {
        imagesets_available.value = JSON.parse(message) as string[];
      }

      if (message_type === "imagesets_update_loaded") {
        imagesets_loaded.value = JSON.parse(message);
      }  

      if (message_type === "imagesets_update_images") {
        let received_object = JSON.parse(message);

        let imageset_name : string = received_object["name"];
        let imageset_images : string[] = received_object["images"];

        imagesets_images.value[imageset_name] = imagesets_images;
      }
    }.bind(this));

  function requestAvailableImagesetsUpdate() {
    sendMessage(websocket.value, encode_messagetype("imagesets_request_available") + " :  ");
  }

  function requestLoadedImagesetsUpdate() {
    sendMessage(websocket.value, encode_messagetype("imagesets_request_loaded") + " :  ");
  }


  function requestImagesInImageset(name: string) {
    sendMessage(websocket.value, encode_messagetype("imagesets_request_images") + " : " + name);
  }


  function requestImportImageset(name : string) {
    sendMessage(websocket.value, encode_messagetype("imagesets_load_imageset") + " : " + name);
  }

  function requestRemoveImageset(name : string) {
    sendMessage(websocket.value, encode_messagetype("imagesets_remove_imageset") + " : " + name);
  }

  function requestActivateImageset(name : string) {
    sendMessage(websocket.value, encode_messagetype("imagesets_activate_imageset") + " : " + name);
  }

  function requestDisableImageset(name: string) {
    sendMessage(websocket.value, encode_messagetype("imagesets_disable_imageset") + " : " + name);
  }

  function requestCreateImageset(name: string) {
    sendMessage(websocket.value, encode_messagetype("imageset_request_create") + " : " + name);
  }

  function requestExportImageset(name: string) {
    sendMessage(websocket.value, encode_messagetype("imageset_request_export") + " : " + name);
  }

  return { websocket, imagesets_available, imagesets_loaded, requestAvailableImagesetsUpdate, requestLoadedImagesetsUpdate, requestImportImageset, requestActivateImageset, requestDisableImageset, requestCreateImageset, requestExportImageset, requestRemoveImageset}
})