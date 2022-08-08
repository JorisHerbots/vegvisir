

<template>
  <main>
    <ConfigurationModal v-if="ModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveImplementation"></ConfigurationModal>
    <TestConfigurationModal v-if="TestModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveTestCase"></TestConfigurationModal>
    <AddImplementationModal @ClickedImplementation="this.Add" v-if="AddModalVisisble" @close="this.AddModalVisisble = false;" :AvailableImplementations="VisibleImplementationsToAdd"></AddImplementationModal>


    <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded m-4 py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" id="inline-full-name" type="text" v-model="testsStore.test.name" placeholder="test name">
    
    
    <button @click="RunClicked()" class="absolute bg-transparent mt-4 right-4 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded">
        Run test
    </button>

    <button @click="ExportClicked()" class="absolute bg-transparent mt-4 right-64 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded">
        Export
    </button>
    <div id="ImplementationsView" class="m-4">
    <ImplementationList @AddClicked="ShowAddClientScreen('client')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test mr-4" :listItems="testsStore.test.configuration.clients"></ImplementationList>
    <ImplementationList @AddClicked="ShowAddClientScreen('shaper')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test mr-4" :listItems="testsStore.test.configuration.shapers"></ImplementationList>
    <ImplementationList @AddClicked="ShowAddClientScreen('server')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test" :listItems="testsStore.test.configuration.servers"></ImplementationList>
    </div>

    <TestCaseList @AddClicked="ShowAddClientScreen('testcase')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="ml-4 mr-4 h-64" :listItems="testsStore.test.configuration.testcases"></TestCaseList>


  </main>
</template>



<script lang="ts">
import axios from 'axios';
import ImplementationList from '@/components/ImplementationList.vue'
import AddImplementationModal from '@/components/AddImplementationModal.vue';
import ConfigurationModal from '@/components/ConfigurationModal.vue';
import TestCaseList from '@/components/TestCaseList.vue';
import TestConfigurationModal from '@/components/TestConfigurationModal.vue';
import { useTestsStore } from '@/stores/UseTestsStore.ts';

export default {
  components: {
    AddImplementationModal,
    ImplementationList,
    ConfigurationModal,
    TestCaseList,
    TestConfigurationModal
},
  props: {
  },
  data: () => ({
    AvailableClients: [],
    AvailableShapers: [],
    AvailableServers: [],
    AvailableTestCases: [],
    VisibleImplementationsToAdd: [],
    ModalVisible: false,
    AddModalVisisble: false,
    Implementations: [],
    ActiveImplementation: {},
    ActiveTestCase: {},
    TestModalVisible: false
    }),
   setup () {
    const testsStore = useTestsStore();

    return {testsStore}
   },
   created() {

    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
    this.GetAndFillAvailableImplementations();
    this.GetAndFillAvailableTestCases();
  },
  methods: {
    ModalAccept(arg) {
      this.ModalVisible = false;
      this.TestModalVisible = false;
    },
    ShowAddClientScreen(type) {
      this.AddModalVisisble = true;

      if (type === "client")
        this.VisibleImplementationsToAdd = this.AvailableClients
      
      if (type === "shaper")
        this.VisibleImplementationsToAdd = this.AvailableShapers
      
      if (type === "server")
        this.VisibleImplementationsToAdd = this.AvailableServers

      if (type === "testcase")
        this.VisibleImplementationsToAdd = this.AvailableTestCases

    },
    RunClicked() {
      let obj = {configuration: {clients: this.testsStore.test.configuration.clients, shapers: this.testsStore.test.configuration.shapers, servers: this.testsStore.test.configuration.servers, testcases: this.testsStore.test.configuration.testcases},  name: this.testsStore.test.name}
      axios({
        url: "http://127.0.0.1:5000/Runtest",
        data: obj,
        method: "POST"
      })   
      .then(response => {
            console.log(response);
      })
      .catch(error => {
        console.log(error);
      })


    },
    download(data, filename, type) {
    var file = new Blob([data], {type: type});
    if (window.navigator.msSaveOrOpenBlob) // IE10+
        window.navigator.msSaveOrOpenBlob(file, filename);
    else { // Others
        var a = document.createElement("a"),
                url = URL.createObjectURL(file);
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(function() {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);  
        }, 0); 
    }
    },
    ExportClicked(){
      let obj = {configuration: {clients: this.testsStore.test.configuration.clients, shapers: this.testsStore.test.configuration.shapers, servers: this.testsStore.test.configuration.servers, testcases: this.testsStore.test.configuration.testcases}, name: this.testsStore.test.name};
      let text = JSON.stringify(obj);

      this.download(text, "test.json", "json");
    },
    RemoveActiveImplementation(ImplementationId){
      this.testsStore.test.configuration.clients = this.testsStore.test.configuration.clients.filter(client => client.active_id != ImplementationId);
      this.testsStore.test.configuration.shapers = this.testsStore.test.configuration.shapers.filter(client => client.active_id != ImplementationId);
      this.testsStore.test.configuration.servers = this.testsStore.test.configuration.servers.filter(client => client.active_id != ImplementationId);
      this.testsStore.test.configuration.testcases = this.testsStore.test.configuration.testcases.filter(client => client.active_id != ImplementationId);
    },
    RemoveActiveClientImplementation(ImplementationId){
      this.testsStore.test.configuration.clients = this.testsStore.test.configuration.clients.filter(client => client.active_id != ImplementationId);
    },
    ImplementationOptions(ImplementationId) {
      
      if (this.testsStore.test.configuration.testcases.find(o => o.active_id === ImplementationId)) {
        this.ActiveTestCase = this.testsStore.test.configuration.testcases.find(o => o.active_id === ImplementationId);     
        this.TestModalVisible = true;
      }
      if (this.testsStore.test.configuration.clients.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.testsStore.test.configuration.clients.find(o => o.active_id === ImplementationId);
      if (this.testsStore.test.configuration.shapers.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.testsStore.test.configuration.shapers.find(o => o.active_id === ImplementationId);
      if (this.testsStore.test.configuration.servers.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.testsStore.test.configuration.servers.find(o => o.active_id === ImplementationId);

      this.ModalVisible = true;
      

    },
    ClientImplementationClicked(ImplementationId) {
      this.ModalVisible = true;
      this.ActiveImplementation = this.testsStore.test.configuration.clients.find(o => o.active_id === ImplementationId);
    },
    GetAndFillAvailableImplementations() {

      /* Remove CORS headers */
      // axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';

      axios({
        url: "http://127.0.0.1:5000/Implementations",
        /*params: deviceID,*/
        method: "GET"
      })
        .then(response => {


            this.Implementations = response.data;
            response = response.data
            for (let i in response){
                if (response[i]["role"][0] === "client")
                {
                  let j = structuredClone(response[i]);
                  j.id = i;
                  this.AvailableClients.push(j);
                }
                else if (response[i]["role"][0] === "shaper")
                {
                  let j = structuredClone(response[i]);
                  j.id = i;
                  this.AvailableShapers.push(j);
                }
                else if (response[i]["role"][0] === "server")
                {
                  let j = structuredClone(response[i]);
                  j.id = i;
                  this.AvailableServers.push(j);
                }
            }
        })
        .catch(error => { 
          console.log(error)
        });

    },
    GetAndFillAvailableTestCases() {
      /* Remove CORS headers */
      // axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';

      axios({
        url: "http://127.0.0.1:5000/Testcases",
        /*params: deviceID,*/
        method: "GET"
      })
        .then(response => {
          
            response = response.data
            for (let i in response){
              this.AvailableTestCases.push(response[i])

            }
            console.log(this.AvailableTestCases);
        })
        .catch(error => { 
          console.log(error)
        });

    },
    Add(Id) {
      if (this.AvailableClients.some(implementation => implementation.id === Id))
        this.AddActiveClient(Id)
      if (this.AvailableShapers.some(implementation => implementation.id === Id))
        this.AddActiveShaper(Id)
      if (this.AvailableServers.some(implementation => implementation.id === Id))
        this.AddActiveServer(Id)
      if (this.AvailableTestCases.some(implementation => implementation.id === Id))
        this.AddActiveTestCase(Id);
    },
    AddActiveTestCase(testCaseId){
      for (let i in this.AvailableTestCases) {
        if (this.AvailableTestCases[i].id === testCaseId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableTestCases[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.parameters) {
            j.parameters[envid].value = j.parameters[envid].default;
          }

          this.testsStore.test.configuration.testcases.push(j) 
        } 
      }
      this.AddModalVisisble = false;      
    },
    AddActiveClient(clientImplementationId) {
      for (let i in this.AvailableClients) {
        if (this.AvailableClients[i].id === clientImplementationId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableClients[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.env) {
            j.env[envid].value = j.env[envid].default;
          }

          this.testsStore.test.configuration.clients.push(j) 
        } 
      }
      this.AddModalVisisble = false;
    },
    AddActiveShaper(shaperImplementationId) {
      for (let i in this.AvailableShapers) {
        if (this.AvailableShapers[i].id === shaperImplementationId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableShapers[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.env) {
            j.env[envid].value = j.env[envid].default;
          }

          this.testsStore.test.configuration.shapers.push(j) 
        } 
      }
      this.AddModalVisisble = false;
    },
    AddActiveServer(serverImplementationId) {
      for (let i in this.AvailableServers) {
        if (this.AvailableServers[i].id === serverImplementationId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableServers[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.env) {
            j.env[envid].value = j.env[envid].default;
          }

          this.testsStore.test.configuration.servers.push(j) 
        } 
      }
      this.AddModalVisisble = false;
    }
  }
};
</script>

<style scoped>

#ImplementationsView {
display: flex;
    /* justify-content: space-evenly; */   
    height: 65vh;
}

.test{
    flex: 1;
}

</style>