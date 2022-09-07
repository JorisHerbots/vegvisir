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

interface Implementation {
  image?: string,
  description?: string,
  url?: string,
  role: string[]
  client: {[key: string] : string},
  env?: any, 
}

interface Implementations {
  [key: string]: Implementation
}

interface Testcases {
  [key: string]: Testcase
}

interface TestcaseParameters {
  name: string,
  type: string,
  description: string,
  default: string
}

interface Testcase {
  id: string,
  name: string,
  parameters?: TestcaseParameters
}



export const useImplementationsStore = defineStore('implementations', () => {
  const implementations = ref<Implementations>({});
  const availableClients = ref<Implementations>({});
  const availableShapers = ref<Implementations>({});
  const availableServers = ref<Implementations>({});
  const availableTestcases = ref<Testcases>({});
  const websocketStore = useWebSocketStore();

  websocketStore.websocket.addEventListener('message', function (event) {

    let split = [event.data.slice(0, 3), event.data.slice(5)];
    let header = split[0]

    let message = split[1]

    if (header === websocketStore.message_type_to_header["implementations_update"]) {
      implementations.value = JSON.parse(message)
      let response : Implementations = JSON.parse(message)
      for (let i in response){
          if (response[i]["role"][0] === "client")
          {
            let j = structuredClone(response[i]);
            j.id = i;
            availableClients.value[i] = j;
          }
          else if (response[i]["role"][0] === "shaper")
          {
            let j = structuredClone(response[i]);
            j.id = i;
            availableShapers.value[i] = j;
          }
          else if (response[i]["role"][0] === "server")
          {
            let j = structuredClone(response[i]);
            j.id = i;
            availableServers.value[i] = j;
          }
      }
    }

    if (header === websocketStore.message_type_to_header["implementations_testcases_update"]) {
      availableTestcases.value = JSON.parse(message);
    }


  }.bind(this));


    function requestImplementationsUpdate() {
        websocketStore.sendOnWebSocket(websocketStore.message_type_to_header["implementations_request"] + " :  ");
    } 

    function requestTestcasesUpdate() {
      websocketStore.sendOnWebSocket(websocketStore.message_type_to_header["implementations_testcases_request"] + " :  ");
    }



  return { availableClients , availableShapers, availableServers, availableTestcases, implementations, requestImplementationsUpdate, requestTestcasesUpdate }

})