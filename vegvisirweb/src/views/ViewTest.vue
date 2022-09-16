

<template>
  <main>

      <div class="font-semibold text-3xl text-teal-500 tracking-tight content-center text-center mt-4">{{testsStore.test.name}}</div>


      <div class="w-96 mr-4 top-4 absolute right-4">
        <div class="flex justify-between mb-1 ">
          <span class="text-base font-medium text-teal-500 dark:text-white">Progress</span>
          <div v-if='testsStore.test.status == "running"'>
            <span class="text-sm font-medium text-teal-500 dark:text-white">{{testsStore.status}}</span>
          </div>
          <div v-if='testsStore.test.status == "done"'>
            <span class="text-sm font-medium text-teal-500 dark:text-white">{{(testsStore.test.configuration.clients.length * testsStore.test.configuration.shapers.length * testsStore.test.configuration.servers.length * testsStore.test.configuration.testcases.length) + " / " + 
              (testsStore.test.configuration.clients.length * testsStore.test.configuration.shapers.length * testsStore.test.configuration.servers.length * testsStore.test.configuration.testcases.length) }}</span>
          </div>
          <div v-if='testsStore.test.status != "done" && testsStore.test.status != "running"'>
            <span class="text-sm font-medium text-teal-500 dark:text-white">{{"0 / " + 
              (testsStore.test.configuration.clients.length * testsStore.test.configuration.shapers.length * testsStore.test.configuration.servers.length * testsStore.test.configuration.testcases.length) }}</span>
          </div>                
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
          <div class="bg-teal-500 h-2.5 rounded-full progress" :style="progressStyle"></div>
        </div>
      </div>

    <ul class="flex flex-wrap text-sm font-medium text-center text-gray-500 border-b border-gray-200 dark:border-gray-700 dark:text-gray-400 content-end mr-4 ml-4">
        <li v-for="(item, index) in Tabs" @click='ActiveTab = item; testsStore.getAllLogFiles(testsStore.test.id);'>
            <a v-if="item == ActiveTab" href="#" aria-current="page" class="inline-block p-4 text-blue-600 bg-gray-100 rounded-t-lg active dark:bg-gray-800 dark:text-blue-500">{{item}}</a>
            <a v-if="item != ActiveTab" href="#" aria-current="page" class="inline-block p-4 rounded-t-lg hover:text-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 dark:hover:text-gray-300">{{item}}</a>
        </li>

        <!-- <li class="mr-2"  @click='ActiveTab = "Logs"'>
            <a href="#" aria-current="page" class="inline-block p-4 text-blue-600 bg-gray-100 rounded-t-lg active dark:bg-gray-800 dark:text-blue-500">Logs</a>
        </li>
        <li class="mr-2" @click='ActiveTab = "Configuration"'>
            <a href="#" class="inline-block p-4 rounded-t-lg hover:text-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 dark:hover:text-gray-300">Configuration</a>
        </li> -->
    </ul>

    
    <div v-if='ActiveTab === "Configuration"'>

    <button @click="EditAndRerun" class="absolute bg-transparent hover:bg-orange-500 text-orange-500 font-semibold hover:text-white py-2 px-4 border border-orange-500 hover:border-transparent rounded z-10 right-4">
      Edit and rerun
    </button>


    <ConfigurationModal v-if="ModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveImplementation" :CanBeModified="false"></ConfigurationModal>
    <TestConfigurationModal v-if="TestModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveTestCase" :CanBeModified="false"></TestConfigurationModal>

      <div id="ImplementationsView" class="m-4 pt-16">
        <ImplementationList @AddClicked="ShowAddClientScreen('client')" @CardClicked="ImplementationOptions"  class="test mr-4" :listItems="testsStore.test.configuration.clients" :CanBeRemoved="false"></ImplementationList>
        <ImplementationList @AddClicked="ShowAddClientScreen('shaper')" @CardClicked="ImplementationOptions"  class="test mr-4" :listItems="testsStore.test.configuration.shapers" :CanBeRemoved="false"></ImplementationList>
        <ImplementationList @AddClicked="ShowAddClientScreen('server')" @CardClicked="ImplementationOptions"  class="test" :listItems="testsStore.test.configuration.servers" :CanBeRemoved="false"></ImplementationList>
      </div>

      <TestCaseList @AddClicked="ShowAddClientScreen('testcase')" @CardClicked="ImplementationOptions" class="pt-16 ml-4 mr-4 h-64" :listItems="testsStore.test.configuration.testcases" :CanBeRemoved="false"></TestCaseList>
    </div>

    <div v-if='ActiveTab === "Logs"'>
      <ViewLogs></ViewLogs>

      <!-- <div v-for="(client_item, client_key, client_index) in testsStore.test.configuration.clients" :key="client_key">
        <div v-for="(shaper_item, shaper_key, shaper_index) in testsStore.test.configuration.shapers" :key="shaper_key">
          <div v-for="(server_item, server_key, server_index) in testsStore.test.configuration.servers" :key="server_key">
            <div v-for="(testcase_item, testcase_key, testcase_index) in testsStore.test.configuration.testcases" :key="testcase_key">
              {{client_item.active_id}} 
              {{shaper_item.active_id}} 
              {{server_item.active_id}}
              {{testcase_item.active_id}}

              <ul>
                  <li v-for="(item, index) in dirs" @click='LogDir += "/" + item; this.UpdateLogs();'>{{item}}</li>
              </ul>
          
            </div>
          </div>
        </div>
      </div> -->

    </div>

    <div v-if='ActiveTab === "Imagesets"'>
      this test requires/used the following imagesets:
      {{testsStore.necessary_imagesets}}


    <button @click="ExportTest" class="absolute bg-transparent hover:bg-orange-500 text-orange-500 font-semibold hover:text-white py-2 px-4 border border-orange-500 hover:border-transparent rounded z-10 right-4">
      Export test and imagesets
    </button>


    </div>

    <div v-if='ActiveTab === "All log files"'>

      <div class="search-wrapper">
        <input id="listOfImplementationsSearch" class="ml-4 mt-4 w-1/2 mr-4 bg-gray-200 appearance-none border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" type="text" v-model="AllLogFilesSearch" placeholder="Search name.."/>
      </div>

      <ul class="divide-y">
        <li v-for="(item, index) in filteredList" @click="GoToURL(item)" class="pt-4 pb-4 ml-4 mr-4">
          <a href="#">{{item}}</a>
        </li>
      </ul>
    </div>

<!--  

  <div class="w-96">
    <div class="flex justify-between mb-1 ">
      <span class="text-base font-medium text-teal-500 dark:text-white">Progress</span>
      <span class="text-sm font-medium text-teal-500 dark:text-white">{{status}}</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
      <div class="bg-teal-500 h-2.5 rounded-full progress" :style="progressStyle"></div>
    </div>
  </div> -->
  </main>
</template>



<script lang="ts">
import axios from 'axios';
import { useTestsStore } from '@/stores/UseTestsStore.ts';
import { storeToRefs } from 'pinia'
import ImplementationList from '@/components/ImplementationList.vue'
import AddImplementationModal from '@/components/AddImplementationModal.vue';
import ConfigurationModal from '@/components/ConfigurationModal.vue';
import TestCaseList from '@/components/TestCaseList.vue';
import TestConfigurationModal from '@/components/TestConfigurationModal.vue';
import ViewLogs from '../components/ViewLogs.vue';
import { useWebSocketStore } from '@/stores/UseWebSocketStore';
import { ref, watch } from 'vue';

export default {
  components: {
    AddImplementationModal,
    ImplementationList,
    ConfigurationModal,
    TestCaseList,
    TestConfigurationModal,
    ViewLogs
},
  props: {
    
  },
  setup() {
    const testsStore = useTestsStore();
    let Tabs = ["Logs", "Configuration", "All log files", "Imagesets"];
    let ActiveTab = "Logs";

    let url : URL = new URL(window.location);
    let parameter : string = url.searchParams.get("id");
    
    // If no id in testsStore.test: we reloaded the page
    // If testsStore.test.id !== parameter, the URL requests a different test than is currently in the testsStore
    if (!("id" in testsStore.test) || testsStore.test.id !== parameter) {
      testsStore.test.id = parameter;

      axios({
        url: "http://127.0.0.1:5000/GetTests",
        /*params: deviceID,*/
        method: "GET"
      })
      .then(response => {
        console.info(response.data)
        testsStore.tests = response.data;
        testsStore.test = testsStore.tests[parameter];
        testsStore.getAllLogFiles(testsStore.test.id);
        testsStore.requestNecessaryImagesets(testsStore.test.id);
   })
      .catch(error => { 
        console.log(error)
      });

    }
    else {
      testsStore.getAllLogFiles(testsStore.test.id);
      testsStore.requestNecessaryImagesets(testsStore.test.id);
    }
    return {testsStore, Tabs, ActiveTab}
  },
  data: () => ({
    ActiveTests: [],
    LastValue: 0,
    status: "No information available yet",
    percent: 0,
    ActiveTab: "Logs",
    ModalVisible: false,
    TestModalVisible: false,
    ActiveImplementation: {},
    ActiveTestCase: {},
    AllLogFilesSearch: "",
    }),

   created() {
    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
    console.log(this.$route.query.id);
  },
  methods: {
    GoToURL(path) {

      path = path.substring(path.search("/logs"))

      let p = "http://127.0.0.1:5000" + path 

      window.open(p);
    },
    ExportTest() {
      const websocket = useWebSocketStore();
      websocket.sendOnWebSocket(websocket.message_type_to_header["export_test_reproducable"] + " : " + JSON.stringify(this.testsStore.test))
    },
    EditAndRerun() {
      console.log(this.ActiveTab)
      // Deep copy
      let temp = JSON.parse(JSON.stringify(this.testsStore.test));
      console.log(temp); 
      temp.name = temp.name + "(1)";


      this.testsStore.test = temp
      this.$router.push({ path: '/configure_test' })
    },
    ModalAccept() {
      this.ModalVisible = false;
      this.TestModalVisible = false;
    },
    ImplementationOptions(ImplementationId) {      
      if (this.testsStore.test.configuration.testcases.find(o => o.active_id === ImplementationId)) {
        this.ActiveTestCase = this.testsStore.test.configuration.testcases.find(o => o.active_id === ImplementationId);     
        this.TestModalVisible = true;
      }
      else {
      if (this.testsStore.test.configuration.clients.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.testsStore.test.configuration.clients.find(o => o.active_id === ImplementationId);
      if (this.testsStore.test.configuration.shapers.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.testsStore.test.configuration.shapers.find(o => o.active_id === ImplementationId);
      if (this.testsStore.test.configuration.servers.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.testsStore.test.configuration.servers.find(o => o.active_id === ImplementationId);

      this.ModalVisible = true;
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
  }
  },
  computed: {

    filteredList() {
      return this.testsStore.log_files.filter(path => {
        return path.toLowerCase().includes(this.AllLogFilesSearch.toLowerCase())
      })
    },
    progressStyle() {
      if (this.testsStore.test.status == "done") {
        return "width: " + 100 + "%;"
      }
      if (this.testsStore.test.status == "running") {
        this.percent = this.testsStore.status.split("/").reduce((a,b) => parseInt(a) / parseInt(b)) * 100;
    
        return "width: " + this.percent.toString() + "%;"
      }
      else 
        return "width: " + 0 + "%;"
    }
  }
};
</script>

<style scoped>

#ImplementationsView {
display: flex;
    /* justify-content: space-evenly; */   
    height: 55vh;
}

.test{
    flex: 1;
}

.progress {
  width:  v-bind('percent')%;
}

.card {
}

#test {
  height: 95vh;
}

#test2 {
  bottom: 0px;
} 

</style>