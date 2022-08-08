import { defineStore } from 'pinia'
import { ref, watch } from 'vue';
import axios from 'axios';

export const useTestsStore = defineStore('post', () => {
  const tests = ref(0);
  const test = ref("test_TODO");
  const websocket = ref(null);
  const status = ref("");
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
  
    }.bind(this));


    function removeTest(testId) {
      delete tests.value[testId]
      if (websocket.value.readyState === 1) {

        websocket.value.send("REM : " + testId.toString())
      }

    }


  return { tests, test, websocket, status, changed, removeTest}

})