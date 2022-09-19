<template>
  <main>

    <ImportTestModal v-if="importModalVisible" @close="importModalVisible = false"></ImportTestModal>
    <div v-if="showError">
      <div id="alert" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-40" role="alert">
        <strong class="font-bold">Error</strong>
        <span class="block sm:inline ml-4">{{errorMessage}}</span>
        <span class="absolute top-0 bottom-0 right-0 px-4 py-3">
          <svg @click="showError = false;" class="fill-current h-6 w-6 text-red-500" role="button" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><title>Close</title><path d="M14.348 14.849a1.2 1.2 0 0 1-1.697 0L10 11.819l-2.651 3.029a1.2 1.2 0 1 1-1.697-1.697l2.758-3.15-2.759-3.152a1.2 1.2 0 1 1 1.697-1.697L10 8.183l2.651-3.031a1.2 1.2 0 1 1 1.697 1.697l-2.758 3.152 2.758 3.15a1.2 1.2 0 0 1 0 1.698z"/></svg>
        </span>
      </div>
    </div>

      <div class="text-center text-5xl font-medium mt-8 mb-32">
        Welcome to Vegvisir!
      </div>
  
  <div v-if="!passwordStore.password_is_set" class="content-center text-xl text-center font-bold w-screen mb-32 ">
    Vegvisir needs your sudo password to work, please enter it <br>
  <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded m-4 py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500 z-1" v-model="password" type="password" id="inline-full-name" placeholder="password">
    
    <button @click="sendPassword" class="mt-4 mb-8 bbg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
        Submit
    </button>
  </div>

    <div class="flex">
      <div class="text-center text-xl font-medium mt-8 flex-1 ml-4 mr-4"> 
        <div class="text-3xl">Would you like to create a new test? <br> </div>

        <button @click="$router.push({ path: '/configure_test' })" class="mt-4 mb-8 bbg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            Create Test
        </button>
      <br>
        A test consists of "testcases" and "implementations": clients, shapers, servers <br>
      <br>
        <ul class="text-left ml-24 text-xl font-medium list-disc">
          <li class="text-left text-xl font-medium">Testcase: scenario describing the content to download and stop condition</li>
          <li class="text-left text-xl font-medium">Client: the client downloading the content</li>
          <li class="text-left text-xl font-medium">Shaper: network simulator</li>
          <li class="text-left text-xl font-medium">Server: the webserver hosting the content </li>
        </ul>
        <br>

        Vegvisir is extensible: you can create your own testcases and implementations, please see the documentation on how to do so.  <br>
      </div>

      <div class="text-center text-xl font-medium mt-8 flex-1">
        <div class="text-3xl">Would you like to import and reproduce a test? <br></div>
        <button @click="if (checkError()){} else {importModalVisible = true};" class=" mt-4 mb-8 bbg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            Import Test
        </button>

        <br>
        The test will be imported and automatically be ran again to reproduce the results

      </div>

      <div class="text-center text-xl font-medium mt-8 flex-1 mr-4 ml-4">
        <div class="text-3xl">Would you like to view past and currently running tests? <br></div>
        <button @click="$router.push({ path: '/progress' })" class=" mt-4 mb-8 bg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            View
        </button>

        <br>
        Past tests can be viewed here as can running tests. Clicking on a test opens the detailed information where you can view the created log files, as well as the configuration of the test. If you would like to re-test a slightly different scenario you can always "edit and rerun" the test.

      </div>

      <div class="text-center text-xl font-medium mt-8 flex-1 hidden">
        <div class="text-3xl">Would you like to break the paraplu?<br></div>
        <a href="https://jherbots.info/"><button class=" mt-4 mb-8 bg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            Break
        </button>
        </a>
      </div>


    </div>

  </main>
</template>


<script lang="ts">
import axios from 'axios';
import { usePasswordStore }  from '@/stores/UsePasswordStore.ts';
import { ref, watch } from 'vue';
import ImportTestModal from '@/components/ImportTestModal.vue';

export default {
  components: {
    ImportTestModal
},
  props: {
    
  },
  setup() {
    const passwordStore = usePasswordStore();
    const importModalVisible = ref<Boolean>(false);
    const showError = ref<Boolean>(false);

    return { passwordStore, importModalVisible, showError }
  },
  data: () => ({
    password: String,
    errorMessage: String
    }),
   created() {
    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
    this.password = ""
  },
  methods: {
    sendPassword() {
      this.passwordStore.setPassword(this.password);
      this.showError = false;
    },
    checkError() {
      if (!this.passwordStore.password_is_set)
      {
        this.errorMessage = "Please fill in and submit your sudo password on the home page"
        this.showError = true;
        return true;
      }
      return false;      
    }
  }
}
</script>