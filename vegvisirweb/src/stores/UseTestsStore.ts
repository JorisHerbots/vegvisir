import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import axios from 'axios';

export const useTestsStore = defineStore('post', () => {
  const tests = ref(0);
  const test = ref({configuration: {servers : [], clients : [], shapers : [], testcases: []}});
  const websocket = ref(null);
  const status = ref("");
  const log_files = ref([]);
  const changed = ref(false);
  
  websocket.value = new WebSocket("ws://127.0.0.1:5000/TestsWebSocket");
  axios({
    url: "http://127.0.0.1:5000/GetTests",
    /*params: deviceID,*/
    method: "GET"
  })
    .then(response => {
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


    function removeTest(testId) {
      console.log("heeer")
      delete tests.value[testId]
      if (websocket.value.readyState === 1) {

        websocket.value.send("REM : " + testId.toString())
      }

    }

    function getAllLogFilesInFolder(folder) {
      if (websocket.value.readyState === 1) {

        websocket.value.send("RLF : " + folder)
      }   
    }

    function getAllLogFiles(testId) {
      console.log("dkfksdjf")
      if (websocket.value.readyState === 1) {

        websocket.value.send("RAL : " + testId.toString())
      } 
      console.log("getting all og file")
    }


  return { tests, test, websocket, log_files, status, changed, removeTest, getAllLogFiles, getAllLogFilesInFolder}

})