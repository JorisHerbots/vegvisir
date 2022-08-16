import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import axios from 'axios';



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

export const useTestsStore = defineStore('post', () => {
  const tests = ref<Testdictionary>({});
  const test = ref({configuration: {servers : [], clients : [], shapers : [], testcases: []}});
  const websocket = ref<WebSocket>();
  const status = ref<string>("");
  const log_files = ref<string[]>([]);
  const changed = ref<boolean>(false);
  
  websocket.value = new WebSocket("ws://127.0.0.1:5000/TestsWebSocket");
  
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


    websocket.value.addEventListener('message', function (event) {

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

    // source: https://gist.github.com/ndrbrt/4fb9af2084316ac0c0f9d3c46b9f2d02 
    const waitForOpenConnection = (socket) => {
      return new Promise((resolve, reject) => {
          const maxNumberOfAttempts = 10
          const intervalTime = 200 //ms
  
          let currentAttempt = 0
          const interval = setInterval(() => {
              if (currentAttempt > maxNumberOfAttempts - 1) {
                  clearInterval(interval)
                  reject(new Error('Maximum number of attempts exceeded'))
              } else if (socket.readyState === socket.OPEN) {
                  clearInterval(interval)
                  resolve()
              }
              currentAttempt++
          }, intervalTime)
      })
  }

  const sendMessage = async (socket, msg) => {
    if (socket.readyState !== socket.OPEN) {
        try {
            await waitForOpenConnection(socket)
            socket.send(msg)
        } catch (err) { console.error(err) }
    } else {
        socket.send(msg)
    }
  }

    function requestRunningTestStatusUpdate() {
      sendMessage(websocket.value, "RSU :  ");
    }


    function removeTest(testId : string) {
      delete tests.value[testId]
      if (websocket.value.readyState === 1) {
        websocket.value.send("REM : " + testId.toString())
      }

    }

    function getAllLogFilesInFolder(folder : string) {
      if (websocket.value.readyState === 1) {

        websocket.value.send("RLF : " + folder)
      }   
    }


  


    function getAllLogFiles(testId : string) {
      if (websocket.value.readyState === 1) {

        websocket.value.send("RAL : " + testId.toString())
      } 
    }


  return { tests, test, websocket, log_files, status, changed, removeTest, getAllLogFiles, getAllLogFilesInFolder, requestRunningTestStatusUpdate}

})