

<template>
  <main>
    <ConfigurationModal v-if="ModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveImplementation" :CanBeModified="true"></ConfigurationModal>
    <TestConfigurationModal v-if="TestModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveTestCase" :CanBeModified="true"></TestConfigurationModal>
    <AddImplementationModal @ClickedImplementation="this.Add" v-if="AddModalVisisble" @close="this.AddModalVisisble = false;" :AvailableImplementations="VisibleImplementationsToAdd"></AddImplementationModal>

    <div v-if="showError">
      <div id="alert" class="absolute bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-40" role="alert">
        <strong class="font-bold">Error</strong>
        <span class="block sm:inline ml-4">{{errorMessage}}</span>
        <span class="absolute top-0 bottom-0 right-0 px-4 py-3">
          <svg @click="showError = false;" class="fill-current h-6 w-6 text-red-500" role="button" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><title>Close</title><path d="M14.348 14.849a1.2 1.2 0 0 1-1.697 0L10 11.819l-2.651 3.029a1.2 1.2 0 1 1-1.697-1.697l2.758-3.15-2.759-3.152a1.2 1.2 0 1 1 1.697-1.697L10 8.183l2.651-3.031a1.2 1.2 0 1 1 1.697 1.697l-2.758 3.152 2.758 3.15a1.2 1.2 0 0 1 0 1.698z"/></svg>
        </span>
      </div>
    </div>

    <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded m-4 py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500 z-1" id="inline-full-name" type="text" v-model="testsStore.test.name" placeholder="test name">
    
    
    <button @click="RunClicked()" class="absolute bg-transparent mt-4 right-4 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded">
        Run test
    </button>
<!-- 
    <button @click="ExportClicked()" class="absolute bg-transparent mt-4 right-64 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded">
        Export
    </button> -->
    <div id="ImplementationsView" class="m-4">
    <ImplementationList @AddClicked="ShowAddClientScreen('client')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test mr-4" listname="clients" :listItems="testsStore.test.configuration.clients" :CanBeModified="true"></ImplementationList>
    <ImplementationList @AddClicked="ShowAddClientScreen('shaper')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test mr-4" listname="shapers" :listItems="testsStore.test.configuration.shapers" :CanBeModified="true"></ImplementationList>
    <ImplementationList @AddClicked="ShowAddClientScreen('server')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test" listname="servers" :listItems="testsStore.test.configuration.servers" :CanBeModified="true"></ImplementationList>
    </div>

    <TestCaseList @AddClicked="ShowAddClientScreen('testcase')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="ml-4 mr-4 h-64" :listItems="testsStore.test.configuration.testcases" :CanBeModified="true"></TestCaseList>


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
import { useImplementationsStore } from '@/stores/UseImplementationsStore';
import { usePasswordStore } from '@/stores/UsePasswordStore';


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
    TestModalVisible: false,
    showError: false,
    errorMessage: String
    }),
   setup () {
    const testsStore = useTestsStore();
    const implementationsStore = useImplementationsStore();
    const passwordStore = usePasswordStore();

    implementationsStore.requestImplementationsUpdate();
    implementationsStore.requestTestcasesUpdate();

    return {testsStore, implementationsStore, passwordStore}
   },
   created() {

    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
  },
  methods: {
    ModalAccept(arg) {
      this.ModalVisible = false;
      this.TestModalVisible = false;
    },
    ShowAddClientScreen(type) {
      this.AddModalVisisble = true;

      if (type === "client")
        this.VisibleImplementationsToAdd = this.implementationsStore.availableClients
      
      if (type === "shaper")
        this.VisibleImplementationsToAdd = this.implementationsStore.availableShapers
      
      if (type === "server")
        this.VisibleImplementationsToAdd = this.implementationsStore.availableServers

      if (type === "testcase")
        this.VisibleImplementationsToAdd = this.implementationsStore.availableTestcases
    },
    RunClicked() {

      if(!this.CheckError())
      {

        let obj = {configuration: {clients: this.testsStore.test.configuration.clients, shapers: this.testsStore.test.configuration.shapers, servers: this.testsStore.test.configuration.servers, testcases: this.testsStore.test.configuration.testcases},  name: this.testsStore.test.name}
        axios({
          url: "http://127.0.0.1:5000/Runtest",
          data: obj,
          method: "POST"
        })   
        .then(response => {
          this.$router.push({ path: '/view_test', query: {id: response.data} })
        })
        .catch(error => {
          console.debug(error);
        })

      this.showError = false;
      }
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
      
      // TODO: why is this not if else with modalvisible

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
    Add(Id) {
      if (this.implementationsStore.availableClients[Id] !== undefined)
        this.AddActive(this.testsStore.test.configuration.clients, this.implementationsStore.availableClients[Id]);
      if (this.implementationsStore.availableShapers[Id] !== undefined)
        this.AddActive(this.testsStore.test.configuration.shapers, this.implementationsStore.availableShapers[Id]);
      if (this.implementationsStore.availableServers[Id] !== undefined)
        this.AddActive(this.testsStore.test.configuration.servers, this.implementationsStore.availableServers[Id]);
      if (this.implementationsStore.availableTestcases[Id] !== undefined)
        this.AddActive(this.testsStore.test.configuration.testcases, this.implementationsStore.availableTestcases[Id]);
    },
    AddActive(location, object) {

      // Deep copy
      let j = JSON.parse(JSON.stringify(object));

      j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

      // Set all env variables to default value
      for (let envid in j.parameters) {
        j.parameters[envid].value = j.parameters[envid].default;
      }

      for (let envid in j.env) {
        j.env[envid].value = j.env[envid].default;
      }

      location.push(j) 

      this.AddModalVisisble = false;      
    },
    CheckError() {
      if (!this.passwordStore.password_is_set)
      {
        this.errorMessage = "Please fill in and submit your sudo password on the home page"
        this.showError = true;
        return true;
      }
      if (this.testsStore.test.name === "" || !("name" in this.testsStore.test)) {
        this.errorMessage = "Please fill in a name"
        this.showError = true;
        return true;
      }
      for (let item in this.testsStore.test.configuration) {
        console.log(item)
        if (this.testsStore.test.configuration[item].length == 0)
        {
          this.errorMessage = "No " + item.substring(0, item.length - 1) + " found, you need at least 1."
          this.showError = true;
          return true;
        }
      }
      
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

#alert {
  top: -50px;
  left: 25vw;
  width: 50vw;
}

</style>