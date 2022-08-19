import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import axios from 'axios';
import { useWebSocketStore } from '@/stores/UseWebSocketStore';


interface Configuration {
  clients: any[],
  servers: any[],
  shapers: any[],
  testcases: any[] 
}

interface Test {
  configuration: Configuration,
  id: string,
  log_dirs?: string[],
  name: string,
  status: string,
  time_added: string
}

interface Testdictionary {
  [key: string]: Test
}

export const useTestsStore = defineStore('tests', () => {
  const tests = ref<Testdictionary>({});
  const test = ref({configuration: {servers : [], clients : [], shapers : [], testcases: []}});
  const status = ref<string>("");
  const log_files = ref<string[]>([]);
  const changed = ref<boolean>(false);
  const websocketStore = useWebSocketStore();
  

  
  axios({
    url: "http://127.0.0.1:5000/GetTests",
    /*params: deviceID,*/
    method: "GET"
  })
    .then(response => {
        console.info(response.data)
        tests.value = response.data;
    })
    .catch(error => { 
      console.log(error)
    });


    websocketStore.websocket.addEventListener('message', function (event) {

      let split = [event.data.slice(0, 3), event.data.slice(5)];
      let header = split[0]

      let message = split[1]

      if (header === "ADD" || header === "UPD") {
        let object = JSON.parse(message)
        tests.value[object.id] = object
      }

      if (header === "PRO") {
        status.value = message;
      }

      if (header === "UAL") {
        log_files.value = JSON.parse(message);
      }
  
  
    }.bind(this));

    function requestRunningTestStatusUpdate() {
      websocketStore.sendOnWebSocket("RSU :  ");
    }


    function removeTest(testId : string) {
      delete tests.value[testId]
      websocketStore.sendOnWebSocket("REM : " + testId.toString())
    }

    function getAllLogFilesInFolder(folder : string) {
      websocketStore.sendOnWebSocket("RLF : " + folder)  
    }

    function getAllLogFiles(testId : string) {
      websocketStore.sendOnWebSocket("RAL : " + testId.toString())
    }


  return { tests, test, log_files, status, changed, removeTest, getAllLogFiles, getAllLogFilesInFolder, requestRunningTestStatusUpdate}

})